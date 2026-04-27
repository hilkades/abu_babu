from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import TgUser


class UsersRepo:
    async def upsert(self, db: AsyncSession, *, user: TgUser) -> None:
        existing = await db.get(TgUser, user.id)
        now = datetime.utcnow()
        if existing is None:
            user.created_at = now
            user.updated_at = now
            db.add(user)
            return
        existing.is_bot = user.is_bot
        existing.username = user.username
        existing.first_name = user.first_name
        existing.last_name = user.last_name
        existing.updated_at = now

