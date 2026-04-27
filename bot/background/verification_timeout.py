from __future__ import annotations

import asyncio

from aiogram import Bot
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.models.enums import TimeoutAction
from bot.repository import AuditRepo, ChatSettingsRepo
from bot.services import VerificationStore
from bot.services.moderation import ModerationService
from bot.utils.logging import get_logger
from bot.utils.time import now_ts


log = get_logger("verif_timeout")


async def verification_timeout_loop(
    *,
    bot: Bot,
    redis: Redis,
    sessionmaker: async_sessionmaker[AsyncSession],
    poll_interval_sec: float = 1.0,
) -> None:
    store = VerificationStore(redis)
    audit = AuditRepo()
    chat_repo = ChatSettingsRepo()
    mod = ModerationService(bot, audit)

    while True:
        try:
            due = await store.pop_due(now_ts=now_ts(), limit=200)
            if not due:
                await asyncio.sleep(poll_interval_sec)
                continue

            for chat_id, message_id in due:
                try:
                    status = await store.mark_expired_if_due(chat_id=chat_id, message_id=message_id, now_ts=now_ts())
                    if status != "expired":
                        continue
                    snap = await store.get_snapshot(chat_id=chat_id, message_id=message_id)
                    if not snap:
                        continue

                    async with sessionmaker() as db:
                        settings = await chat_repo.get(db, chat_id=chat_id)

                        await audit.add_audit(
                            db,
                            chat_id=chat_id,
                            actor_user_id=None,
                            action="verification_expired",
                            payload={"message_id": message_id, "user_id": snap.user_id},
                        )

                        await mod.delete_message(db, chat_id=chat_id, message_id=message_id)

                        action = TimeoutAction(settings.timeout_action)
                        if action == TimeoutAction.delete:
                            await db.commit()
                            continue
                        if action == TimeoutAction.mute:
                            await mod.mute(
                                db,
                                chat_id=chat_id,
                                user_id=snap.user_id,
                                seconds=max(int(settings.flood_mute_sec), 120),
                                reason="verification_timeout",
                            )
                        elif action == TimeoutAction.kick:
                            await mod.kick(db, chat_id=chat_id, user_id=snap.user_id, reason="verification_timeout")
                        elif action == TimeoutAction.ban:
                            await mod.ban(db, chat_id=chat_id, user_id=snap.user_id, reason="verification_timeout")

                        await db.commit()
                except Exception as e:
                    log.exception("due_item_error", chat_id=chat_id, message_id=message_id, err=str(e))
        except Exception as e:
            log.exception("loop_error", err=str(e))
            await asyncio.sleep(2.0)

