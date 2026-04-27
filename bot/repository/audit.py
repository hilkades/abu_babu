from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import AuditLog, ModerationAction


class AuditRepo:
    async def add_audit(
        self,
        db: AsyncSession,
        *,
        chat_id: int | None,
        actor_user_id: int | None,
        action: str,
        payload: dict,
    ) -> None:
        db.add(
            AuditLog(
                chat_id=chat_id,
                actor_user_id=actor_user_id,
                action=action,
                payload=payload,
                created_at=datetime.utcnow(),
            )
        )

    async def add_moderation_action(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        user_id: int | None,
        message_id: int | None,
        action_type: str,
        details: dict,
    ) -> None:
        db.add(
            ModerationAction(
                chat_id=chat_id,
                user_id=user_id,
                message_id=message_id,
                action_type=action_type,
                details=details,
                created_at=datetime.utcnow(),
            )
        )

    async def last_audit(self, db: AsyncSession, *, chat_id: int, limit: int = 10) -> list[AuditLog]:
        q = select(AuditLog).where(AuditLog.chat_id == chat_id).order_by(AuditLog.created_at.desc()).limit(limit)
        res = await db.execute(q)
        return list(res.scalars().all())

