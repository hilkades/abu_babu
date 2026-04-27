from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


async def is_user_admin(bot: Bot, *, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    except (TelegramForbiddenError, TelegramBadRequest):
        return False
    return member.status in ("creator", "administrator")

