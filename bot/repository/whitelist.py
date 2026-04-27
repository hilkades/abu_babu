from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import UserWhitelist


class WhitelistRepo:
    async def add(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        user_id: int,
        ttl_sec: int | None,
        reason: str | None = None,
    ) -> None:
        expires_at = None
        if ttl_sec and ttl_sec > 0:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_sec)
        # upsert-like: delete then insert (simple, safe)
        await db.execute(delete(UserWhitelist).where(UserWhitelist.chat_id == chat_id, UserWhitelist.user_id == user_id))
        db.add(
            UserWhitelist(
                chat_id=chat_id,
                user_id=user_id,
                expires_at=expires_at,
                reason=reason,
                created_at=datetime.utcnow(),
            )
        )

    async def remove(self, db: AsyncSession, *, chat_id: int, user_id: int) -> int:
        res = await db.execute(delete(UserWhitelist).where(UserWhitelist.chat_id == chat_id, UserWhitelist.user_id == user_id))
        return res.rowcount or 0

    async def is_whitelisted(self, db: AsyncSession, *, chat_id: int, user_id: int) -> bool:
        q = (
            select(UserWhitelist.id)
            .where(UserWhitelist.chat_id == chat_id, UserWhitelist.user_id == user_id)
            .limit(1)
        )
        res = await db.execute(q)
        return res.first() is not None

