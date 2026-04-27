from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Chat, ChatSettings, StrictnessMode, TimeoutAction


class ChatSettingsRepo:
    def _find_pending_settings(self, db: AsyncSession, chat_id: int) -> ChatSettings | None:
        # If ChatSettings was already added in this transaction, db.get() may still return None
        # before flush. Avoid creating duplicates.
        for obj in db.new:
            if isinstance(obj, ChatSettings) and obj.chat_id == chat_id:
                return obj
        return None

    async def ensure_chat(self, db: AsyncSession, *, chat_id: int, title: str | None) -> None:
        chat = await db.get(Chat, chat_id)
        now = datetime.utcnow()
        if chat is None:
            chat = Chat(id=chat_id, title=title, created_at=now, updated_at=now)
            db.add(chat)
            db.add(ChatSettings(chat_id=chat_id, created_at=now, updated_at=now))
            await db.flush()
            return
        chat.title = title
        chat.updated_at = now
        settings = self._find_pending_settings(db, chat_id) or await db.get(ChatSettings, chat_id)
        if settings is None:
            db.add(ChatSettings(chat_id=chat_id, created_at=now, updated_at=now))
            await db.flush()

    async def get(self, db: AsyncSession, *, chat_id: int) -> ChatSettings:
        settings = self._find_pending_settings(db, chat_id) or await db.get(ChatSettings, chat_id)
        if settings is None:
            # Should not happen if ensure_chat is used, but keep safe
            settings = ChatSettings(chat_id=chat_id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            db.add(settings)
            await db.flush()
        return settings

    async def set_enabled(self, db: AsyncSession, *, chat_id: int, enabled: bool) -> None:
        settings = await self.get(db, chat_id=chat_id)
        settings.enabled = enabled
        settings.updated_at = datetime.utcnow()

    async def set_mode(self, db: AsyncSession, *, chat_id: int, mode: StrictnessMode) -> None:
        settings = await self.get(db, chat_id=chat_id)
        settings.mode = mode.value
        settings.updated_at = datetime.utcnow()

    async def set_timeout(self, db: AsyncSession, *, chat_id: int, seconds: int) -> None:
        settings = await self.get(db, chat_id=chat_id)
        settings.confirm_timeout_sec = seconds
        settings.updated_at = datetime.utcnow()

    async def set_action(self, db: AsyncSession, *, chat_id: int, action: TimeoutAction) -> None:
        settings = await self.get(db, chat_id=chat_id)
        settings.timeout_action = action.value
        settings.updated_at = datetime.utcnow()

