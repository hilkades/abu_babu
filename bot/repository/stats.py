from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import AuditLog, ModerationAction


class StatsRepo:
    async def chat_stats(self, db: AsyncSession, *, chat_id: int, days: int = 1) -> dict[str, int]:
        since = datetime.utcnow() - timedelta(days=days)

        analyzed_q = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.chat_id == chat_id, AuditLog.action == "message_analyzed", AuditLog.created_at >= since)
        )
        analyzed = int((await db.execute(analyzed_q)).scalar() or 0)

        deleted_q = (
            select(func.count())
            .select_from(ModerationAction)
            .where(
                ModerationAction.chat_id == chat_id,
                ModerationAction.action_type == "delete_message",
                ModerationAction.created_at >= since,
            )
        )
        deleted = int((await db.execute(deleted_q)).scalar() or 0)

        banned_q = (
            select(func.count())
            .select_from(ModerationAction)
            .where(
                ModerationAction.chat_id == chat_id,
                ModerationAction.action_type == "ban_user",
                ModerationAction.created_at >= since,
            )
        )
        banned = int((await db.execute(banned_q)).scalar() or 0)

        confirmed_q = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.chat_id == chat_id,
                AuditLog.action == "verification_confirmed",
                AuditLog.created_at >= since,
            )
        )
        confirmed = int((await db.execute(confirmed_q)).scalar() or 0)

        expired_q = (
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.chat_id == chat_id,
                AuditLog.action == "verification_expired",
                AuditLog.created_at >= since,
            )
        )
        expired = int((await db.execute(expired_q)).scalar() or 0)

        return {
            "analyzed": analyzed,
            "deleted": deleted,
            "banned": banned,
            "confirmed": confirmed,
            "expired": expired,
        }

