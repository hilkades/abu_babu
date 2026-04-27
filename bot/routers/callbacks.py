from __future__ import annotations

import hmac

from aiogram import Router
from aiogram import Bot
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import StrictnessMode, TimeoutAction
from bot.repository import AuditRepo, ChatSettingsRepo
from bot.services import TrustStore, VerificationStore
from bot.utils.crypto import hmac_sha256_hex
from bot.utils.time import now_ts
from bot.ux import settings_keyboard

callbacks_router = Router(name="callbacks")


@callbacks_router.callback_query()
async def on_callback(call: CallbackQuery, bot: Bot, db: AsyncSession, redis: Redis) -> None:
    if not call.data or not call.message:
        await call.answer()
        return

    if call.data.startswith("s1|"):
        # s1|{chat_id}|{actor_user_id}|{op}|{sig}
        try:
            _v, chat_id_s, actor_s, op, sig = call.data.split("|", 4)
            chat_id = int(chat_id_s)
            actor_user_id = int(actor_s)
        except Exception:
            await call.answer("Некорректная кнопка.", show_alert=True)
            return
        if call.from_user.id != actor_user_id:
            await call.answer("Эта кнопка не для вас.", show_alert=True)
            return
        base = f"s1|{chat_id}|{actor_user_id}|{op}"
        expected_sig = hmac_sha256_hex(bot.token.encode("utf-8"), base.encode("utf-8"))[:12]
        if not hmac.compare_digest(sig, expected_sig):
            await call.answer("Кнопка устарела/недействительна.", show_alert=True)
            return

        repo = ChatSettingsRepo()
        await repo.ensure_chat(db, chat_id=chat_id, title=call.message.chat.title)
        s = await repo.get(db, chat_id=chat_id)
        if op == "toggle":
            s.enabled = not bool(s.enabled)
        elif op == "cycle_mode":
            order = [StrictnessMode.lenient.value, StrictnessMode.balanced.value, StrictnessMode.strict.value]
            try:
                idx = order.index(str(s.mode))
                s.mode = order[(idx + 1) % len(order)]
            except Exception:
                s.mode = StrictnessMode.balanced.value
        elif op == "cycle_action":
            order = [TimeoutAction.delete.value, TimeoutAction.mute.value, TimeoutAction.kick.value, TimeoutAction.ban.value]
            try:
                idx = order.index(str(s.timeout_action))
                s.timeout_action = order[(idx + 1) % len(order)]
            except Exception:
                s.timeout_action = TimeoutAction.delete.value
        else:
            await call.answer()
            return

        await AuditRepo().add_audit(
            db,
            chat_id=chat_id,
            actor_user_id=actor_user_id,
            action="settings_changed",
            payload={"op": op, "enabled": s.enabled, "mode": s.mode, "timeout_action": s.timeout_action},
        )

        try:
            await call.message.edit_reply_markup(
                reply_markup=settings_keyboard(
                    bot.token,
                    chat_id=chat_id,
                    actor_user_id=actor_user_id,
                    enabled=bool(s.enabled),
                    mode=str(s.mode),
                    timeout_action=str(s.timeout_action),
                )
            )
        except Exception:
            pass
        await call.answer("Ок.", show_alert=False)
        return

    if not call.data.startswith("v1|"):
        await call.answer()
        return

    # v1|{message_id}|{user_id}|{token}|{sig}
    try:
        _v, msg_id_s, user_id_s, token, sig = call.data.split("|", 4)
        orig_message_id = int(msg_id_s)
        expected_user_id = int(user_id_s)
    except Exception:
        await call.answer("Некорректная кнопка.", show_alert=True)
        return

    chat_id = call.message.chat.id
    if call.from_user.id != expected_user_id:
        await call.answer("Эта кнопка не для вас.", show_alert=True)
        return

    expected_sig = hmac_sha256_hex(
        bot.token.encode("utf-8"),
        f"{chat_id}:{orig_message_id}:{expected_user_id}:{token}".encode("utf-8"),
    )[:12]
    if not hmac.compare_digest(sig, expected_sig):
        await call.answer("Кнопка устарела/недействительна.", show_alert=True)
        return

    store = VerificationStore(redis)
    res = await store.confirm(
        chat_id=chat_id,
        message_id=orig_message_id,
        user_id=expected_user_id,
        token_plain=token,
        now_ts=now_ts(),
    )

    audit = AuditRepo()
    if not res.ok:
        await audit.add_audit(
            db,
            chat_id=chat_id,
            actor_user_id=call.from_user.id,
            action="verification_failed",
            payload={"message_id": orig_message_id, "reason": res.reason},
        )
        await call.answer("Не удалось подтвердить (возможно, истекло время).", show_alert=True)
        return

    settings = await ChatSettingsRepo().get(db, chat_id=chat_id)
    if settings.whitelist_after_confirm:
        await TrustStore(redis).trust(
            chat_id=chat_id, user_id=expected_user_id, ttl_sec=int(settings.whitelist_ttl_sec)
        )

    await audit.add_audit(
        db,
        chat_id=chat_id,
        actor_user_id=call.from_user.id,
        action="verification_confirmed",
        payload={"message_id": orig_message_id},
    )

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.answer("Спасибо! Подтверждение принято.", show_alert=False)

