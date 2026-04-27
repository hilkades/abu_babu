from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatPermissions
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.enums import ModerationActionType
from bot.repository import AuditRepo
from bot.utils.logging import get_logger


log = get_logger("moderation")


@dataclass(frozen=True)
class ModerationResult:
    ok: bool
    reason: str  # "ok" | "forbidden" | "bad_request" | "error"


class ModerationService:
    def __init__(self, bot: Bot, audit_repo: AuditRepo) -> None:
        self._bot = bot
        self._audit = audit_repo

    async def delete_message(self, db: AsyncSession, *, chat_id: int, message_id: int) -> ModerationResult:
        try:
            await self._bot.delete_message(chat_id=chat_id, message_id=message_id)
            await self._audit.add_moderation_action(
                db,
                chat_id=chat_id,
                user_id=None,
                message_id=message_id,
                action_type=ModerationActionType.delete_message.value,
                details={},
            )
            return ModerationResult(ok=True, reason="ok")
        except TelegramForbiddenError as e:
            log.warning("delete_forbidden", chat_id=chat_id, message_id=message_id, err=str(e))
            return ModerationResult(ok=False, reason="forbidden")
        except TelegramBadRequest as e:
            # message to delete not found / already deleted
            log.info("delete_bad_request", chat_id=chat_id, message_id=message_id, err=str(e))
            return ModerationResult(ok=False, reason="bad_request")
        except Exception as e:
            log.exception("delete_error", chat_id=chat_id, message_id=message_id, err=str(e))
            return ModerationResult(ok=False, reason="error")

    async def mute(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        user_id: int,
        seconds: int,
        reason: str | None = None,
    ) -> ModerationResult:
        until = datetime.utcnow() + timedelta(seconds=seconds)
        try:
            perms = ChatPermissions(can_send_messages=False)
            await self._bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=perms,
                until_date=until,
            )
            await self._audit.add_moderation_action(
                db,
                chat_id=chat_id,
                user_id=user_id,
                message_id=None,
                action_type=ModerationActionType.restrict_user.value,
                details={"seconds": seconds, "reason": reason},
            )
            return ModerationResult(ok=True, reason="ok")
        except TelegramForbiddenError as e:
            log.warning("mute_forbidden", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="forbidden")
        except TelegramBadRequest as e:
            log.info("mute_bad_request", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="bad_request")
        except Exception as e:
            log.exception("mute_error", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="error")

    async def ban(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        user_id: int,
        reason: str | None = None,
    ) -> ModerationResult:
        try:
            await self._bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await self._audit.add_moderation_action(
                db,
                chat_id=chat_id,
                user_id=user_id,
                message_id=None,
                action_type=ModerationActionType.ban_user.value,
                details={"reason": reason},
            )
            return ModerationResult(ok=True, reason="ok")
        except TelegramForbiddenError as e:
            log.warning("ban_forbidden", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="forbidden")
        except TelegramBadRequest as e:
            # user already banned / not found etc
            log.info("ban_bad_request", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="bad_request")
        except Exception as e:
            log.exception("ban_error", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="error")

    async def kick(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        user_id: int,
        reason: str | None = None,
    ) -> ModerationResult:
        """
        Telegram "kick" = ban + immediate unban (user removed, can rejoin).
        """
        try:
            await self._bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await self._bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
            await self._audit.add_moderation_action(
                db,
                chat_id=chat_id,
                user_id=user_id,
                message_id=None,
                action_type=ModerationActionType.kick_user.value,
                details={"reason": reason},
            )
            return ModerationResult(ok=True, reason="ok")
        except TelegramForbiddenError as e:
            log.warning("kick_forbidden", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="forbidden")
        except TelegramBadRequest as e:
            log.info("kick_bad_request", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="bad_request")
        except Exception as e:
            log.exception("kick_error", chat_id=chat_id, user_id=user_id, err=str(e))
            return ModerationResult(ok=False, reason="error")

