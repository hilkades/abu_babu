from __future__ import annotations

from aiogram import Router
from aiogram import Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.repository import ChatSettingsRepo

user_router = Router(name="user")


@user_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Я антиспам-бот для групп.\n"
        "Добавьте меня в чат и выдайте права администратора (удаление/бан/ограничения).\n"
        "Команды: /help"
    )


@user_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Команды:\n"
        "- /status — статус защиты\n"
        "- /settings — меню настроек (админы)\n"
        "- /audit — последние действия (админы)\n"
        "- /stats — статистика (админы)\n"
    )


@user_router.message(Command("status"))
async def cmd_status(message: Message, bot: Bot, db: AsyncSession) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Добавьте меня в групповой чат, чтобы показывать статус защиты.")
        return
    repo = ChatSettingsRepo()
    await repo.ensure_chat(db, chat_id=message.chat.id, title=message.chat.title)
    s = await repo.get(db, chat_id=message.chat.id)
    await message.answer(
        "Антиспам статус:\n"
        f"- enabled: {s.enabled}\n"
        f"- mode: {s.mode}\n"
        f"- confirm_timeout_sec: {s.confirm_timeout_sec}\n"
        f"- timeout_action: {s.timeout_action}\n"
        f"- anti_flood: {s.anti_flood_enabled}\n"
    )

