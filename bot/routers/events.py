from __future__ import annotations

from datetime import datetime
import re

from aiogram import Router
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.antispam import extract_features, score_message
from bot.antispam.config import normalize_mode
from bot.models.enums import RiskLevel
from bot.repository import AuditRepo, ChatSettingsRepo, UsersRepo
from bot.services import BadwordsStore, FloodLimiter, TrustStore, VerificationStore
from bot.services.moderation import ModerationService
from bot.utils.crypto import hmac_sha256_hex, random_token, sha256_hex
from bot.utils.time import now_ts

events_router = Router(name="events")


@events_router.message()
async def on_message(message: Message, bot: Bot, db: AsyncSession, redis: Redis) -> None:
    if message.chat.type not in ("group", "supergroup"):
        return
    if not message.from_user or message.from_user.is_bot:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    chat_repo = ChatSettingsRepo()
    users_repo = UsersRepo()
    audit_repo = AuditRepo()

    await chat_repo.ensure_chat(db, chat_id=chat_id, title=message.chat.title)
    # avoid import cycles: construct SQLAlchemy model directly
    from bot.models import TgUser  # local import

    await users_repo.upsert(
        db,
        user=TgUser(
            id=user_id,
            is_bot=bool(message.from_user.is_bot),
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        ),
    )

    settings = await chat_repo.get(db, chat_id=chat_id)
    if not settings.enabled:
        return

    # Backward compatibility: move legacy per-chat bad words into shared file list.
    BadwordsStore.merge(set(settings.bad_keywords or []))

    # Hard rule: chat badwords => delete immediately (even if user is trusted/verified)
    features = extract_features(message)
    text_cf = (features.text or "").casefold()
    badwords_cf = BadwordsStore.load_set()
    literal_badwords, regex_badwords = BadwordsStore.split_rules(badwords_cf)
    matched_badword = False
    if text_cf:
        if literal_badwords and any(kw in text_cf for kw in literal_badwords):
            matched_badword = True
        elif regex_badwords:
            for pattern in regex_badwords:
                try:
                    if re.search(pattern, text_cf, flags=re.IGNORECASE):
                        matched_badword = True
                        break
                except re.error:
                    if pattern.casefold() in text_cf:
                        matched_badword = True
                        break
    if matched_badword:
        mod = ModerationService(bot, audit_repo)
        await mod.delete_message(db, chat_id=chat_id, message_id=message.message_id)
        await audit_repo.add_audit(
            db,
            chat_id=chat_id,
            actor_user_id=None,
            action="badword_deleted",
            payload={"user_id": user_id, "message_id": message.message_id},
        )
        return

    trust = TrustStore(redis)
    if await trust.is_trusted(chat_id=chat_id, user_id=user_id):
        return

    # repeated text burst (behavioral): same normalized text 3+ times in 60s => delete as spam
    norm_text = (message.text or message.caption or "").strip().lower()
    if norm_text and len(norm_text) >= 6:
        h = sha256_hex(norm_text.encode("utf-8"))[:16]
        rep_key = f"repeat:{chat_id}:{user_id}:{h}"
        try:
            cnt = await redis.incr(rep_key)
            if cnt == 1:
                await redis.expire(rep_key, 60)
            if cnt >= 3:
                mod = ModerationService(bot, audit_repo)
                await mod.delete_message(db, chat_id=chat_id, message_id=message.message_id)
                await audit_repo.add_audit(
                    db,
                    chat_id=chat_id,
                    actor_user_id=None,
                    action="repeated_text_deleted",
                    payload={"user_id": user_id, "message_id": message.message_id, "count": int(cnt)},
                )
                return
        except Exception:
            pass

    if settings.anti_flood_enabled:
        limiter = FloodLimiter(redis)
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        flood = await limiter.check(
            chat_id=chat_id,
            user_id=user_id,
            now_ms=now_ms,
            window_sec=int(settings.flood_window_sec),
            max_messages=int(settings.flood_max_messages),
        )
        if not flood.allowed:
            mod = ModerationService(bot, audit_repo)
            await mod.mute(
                db,
                chat_id=chat_id,
                user_id=user_id,
                seconds=int(settings.flood_mute_sec),
                reason="anti_flood",
            )
            await audit_repo.add_audit(
                db,
                chat_id=chat_id,
                actor_user_id=None,
                action="flood_triggered",
                payload={"user_id": user_id, "count": flood.count},
            )
            return

    mode = normalize_mode(settings.mode)
    analysis = score_message(
        features,
        mode=mode,
        allowed_domains=set(settings.allowed_domains or []),
        extra_bad_keywords=literal_badwords,
        extra_bad_keywords_regex=regex_badwords,
        override_weights=settings.weights or None,
        override_thresholds=settings.thresholds or None,
    )

    await audit_repo.add_audit(
        db,
        chat_id=chat_id,
        actor_user_id=None,
        action="message_analyzed",
        payload={
            "user_id": user_id,
            "message_id": message.message_id,
            "risk_level": analysis.risk_level.value,
            "score": analysis.score,
            "reasons": analysis.reasons,
        },
    )

    mod = ModerationService(bot, audit_repo)

    if analysis.risk_level == RiskLevel.safe:
        return

    # Hard rule: any chat "bad word" match => delete immediately (no verification)
    if "bad_keyword" in (analysis.reasons or {}):
        await mod.delete_message(db, chat_id=chat_id, message_id=message.message_id)
        await audit_repo.add_audit(
            db,
            chat_id=chat_id,
            actor_user_id=None,
            action="badword_deleted",
            payload={"user_id": user_id, "message_id": message.message_id, "reasons": analysis.reasons},
        )
        return
    if analysis.risk_level == RiskLevel.spam:
        await mod.delete_message(db, chat_id=chat_id, message_id=message.message_id)
        return
    if analysis.risk_level == RiskLevel.critical:
        await mod.delete_message(db, chat_id=chat_id, message_id=message.message_id)
        await mod.ban(db, chat_id=chat_id, user_id=user_id, reason="critical_spam")
        return

    # suspicious
    token = random_token(8)
    sig = hmac_sha256_hex(
        bot.token.encode("utf-8"),
        f"{chat_id}:{message.message_id}:{user_id}:{token}".encode("utf-8"),
    )[:12]
    callback_data = f"v1|{message.message_id}|{user_id}|{token}|{sig}"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Я человек", callback_data=callback_data)]]
    )

    expires_at = now_ts() + int(settings.confirm_timeout_sec)
    store = VerificationStore(redis)
    await store.create_if_absent(
        chat_id=chat_id,
        message_id=message.message_id,
        user_id=user_id,
        token_plain=token,
        expires_at=expires_at,
        ttl_sec=int(settings.confirm_timeout_sec) + 60,
    )

    prompt = (
        "Система защиты чата просит подтвердить, что вы человек.\n"
        "Нажмите кнопку «Я человек» в течение ограниченного времени."
    )
    try:
        await message.reply(prompt, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        return

