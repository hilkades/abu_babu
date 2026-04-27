from __future__ import annotations

from aiogram import Router
from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import StrictnessMode, TimeoutAction
from bot.repository import AuditRepo, ChatSettingsRepo, StatsRepo, WhitelistRepo
from bot.services import BadwordsStore, TrustStore
from bot.utils.telegram import is_user_admin
from bot.ux import settings_keyboard

admin_router = Router(name="admin")


async def _require_admin(message: Message, bot: Bot) -> bool:
    if message.chat.type not in ("group", "supergroup") or not message.from_user:
        return False
    if await is_user_admin(bot, chat_id=message.chat.id, user_id=message.from_user.id):
        return True
    await message.reply("Команда доступна только администраторам чата.")
    return False


@admin_router.message(Command("enable"))
async def cmd_enable(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    repo = ChatSettingsRepo()
    await repo.ensure_chat(db, chat_id=message.chat.id, title=message.chat.title)
    await repo.set_enabled(db, chat_id=message.chat.id, enabled=True)
    await AuditRepo().add_audit(db, chat_id=message.chat.id, actor_user_id=message.from_user.id, action="enable", payload={})
    await message.reply("Антиспам включён.")


@admin_router.message(Command("disable"))
async def cmd_disable(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    repo = ChatSettingsRepo()
    await repo.ensure_chat(db, chat_id=message.chat.id, title=message.chat.title)
    await repo.set_enabled(db, chat_id=message.chat.id, enabled=False)
    await AuditRepo().add_audit(db, chat_id=message.chat.id, actor_user_id=message.from_user.id, action="disable", payload={})
    await message.reply("Антиспам выключён.")


@admin_router.message(Command("settimeout"))
async def cmd_settimeout(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.reply("Использование: /settimeout <секунды>")
        return
    sec = max(10, min(int(parts[1]), 3600))
    repo = ChatSettingsRepo()
    await repo.set_timeout(db, chat_id=message.chat.id, seconds=sec)
    await message.reply(f"Timeout подтверждения установлен: {sec} сек.")


@admin_router.message(Command("setmode"))
async def cmd_setmode(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.reply("Использование: /setmode strict|balanced|lenient")
        return
    try:
        mode = StrictnessMode(parts[1])
    except Exception:
        await message.reply("Неверный режим. Варианты: strict|balanced|lenient")
        return
    await ChatSettingsRepo().set_mode(db, chat_id=message.chat.id, mode=mode)
    await message.reply(f"Режим установлен: {mode.value}")


@admin_router.message(Command("setaction"))
async def cmd_setaction(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.reply("Использование: /setaction delete|mute|kick|ban")
        return
    try:
        action = TimeoutAction(parts[1])
    except Exception:
        await message.reply("Неверное действие. Варианты: delete|mute|kick|ban")
        return
    await ChatSettingsRepo().set_action(db, chat_id=message.chat.id, action=action)
    await message.reply(f"Действие по таймауту: {action.value}")


@admin_router.message(Command("setthreshold"))
async def cmd_setthreshold(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split()
    if len(parts) != 4:
        await message.reply("Использование: /setthreshold <suspicious> <spam> <critical>")
        return
    try:
        suspicious, spam, critical = map(int, parts[1:4])
    except Exception:
        await message.reply("Пороги должны быть числами.")
        return
    settings = await ChatSettingsRepo().get(db, chat_id=message.chat.id)
    settings.thresholds = {"suspicious": suspicious, "spam": spam, "critical": critical}
    await message.reply(f"Пороги установлены: suspicious={suspicious}, spam={spam}, critical={critical}")


@admin_router.message(Command("setflood"))
async def cmd_setflood(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split()
    if len(parts) != 4:
        await message.reply("Использование: /setflood <window_sec> <max_messages> <mute_sec>")
        return
    try:
        window_sec, max_messages, mute_sec = map(int, parts[1:4])
    except Exception:
        await message.reply("Аргументы должны быть числами.")
        return
    settings = await ChatSettingsRepo().get(db, chat_id=message.chat.id)
    settings.anti_flood_enabled = True
    settings.flood_window_sec = max(2, window_sec)
    settings.flood_max_messages = max(2, max_messages)
    settings.flood_mute_sec = max(10, mute_sec)
    await message.reply(
        f"Антифлуд: окно={settings.flood_window_sec}s, лимит={settings.flood_max_messages}, mute={settings.flood_mute_sec}s"
    )


@admin_router.message(Command("adddomain"))
async def cmd_adddomain(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Использование: /adddomain example.com")
        return
    domain = parts[1].strip().lower()
    settings = await ChatSettingsRepo().get(db, chat_id=message.chat.id)
    domains = set(settings.allowed_domains or [])
    domains.add(domain)
    settings.allowed_domains = sorted(domains)
    await message.reply(f"Разрешённый домен добавлен: {domain}")


@admin_router.message(Command("removedomain"))
async def cmd_removedomain(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Использование: /removedomain example.com")
        return
    domain = parts[1].strip().lower()
    settings = await ChatSettingsRepo().get(db, chat_id=message.chat.id)
    domains = set(settings.allowed_domains or [])
    domains.discard(domain)
    settings.allowed_domains = sorted(domains)
    await message.reply(f"Разрешённый домен удалён: {domain}")


@admin_router.message(Command("addbadword"))
async def cmd_addbadword(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Использование: /addbadword слово_или_фраза")
        return
    kw = parts[1].strip().casefold()
    added = BadwordsStore.add(kw)
    if added:
        await message.reply(f"Запрещённое слово добавлено (глобально): {kw}")
        return
    await message.reply(f"Слово уже есть в глобальном списке: {kw}")


@admin_router.message(Command("removebadword"))
async def cmd_removebadword(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Использование: /removebadword слово_или_фраза")
        return
    kw = parts[1].strip().casefold()
    removed = BadwordsStore.remove(kw)
    if removed:
        await message.reply(f"Запрещённое слово удалено (глобально): {kw}")
        return
    await message.reply(f"Слова нет в глобальном списке: {kw}")


@admin_router.message(Command("addwhitelist"))
async def cmd_addwhitelist(message: Message, bot: Bot, db: AsyncSession, redis: Redis) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply("Использование: /addwhitelist <user_id> [ttl_sec]")
        return
    try:
        target_user_id = int(parts[1])
    except Exception:
        await message.reply("user_id должен быть числом.")
        return
    ttl = None
    if len(parts) >= 3:
        try:
            ttl = int(parts[2])
        except Exception:
            ttl = None
    settings = await ChatSettingsRepo().get(db, chat_id=message.chat.id)
    ttl_sec = ttl if ttl is not None else int(settings.whitelist_ttl_sec)
    await WhitelistRepo().add(db, chat_id=message.chat.id, user_id=target_user_id, ttl_sec=ttl_sec, reason="manual")
    await TrustStore(redis).trust(chat_id=message.chat.id, user_id=target_user_id, ttl_sec=ttl_sec)
    await message.reply(f"Пользователь {target_user_id} добавлен в whitelist на {ttl_sec} сек.")


@admin_router.message(Command("removewhitelist"))
async def cmd_removewhitelist(message: Message, bot: Bot, db: AsyncSession, redis: Redis) -> None:
    if not await _require_admin(message, bot):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.reply("Использование: /removewhitelist <user_id>")
        return
    try:
        target_user_id = int(parts[1])
    except Exception:
        await message.reply("user_id должен быть числом.")
        return
    removed = await WhitelistRepo().remove(db, chat_id=message.chat.id, user_id=target_user_id)
    # best-effort remove redis trust
    try:
        from bot.services.redis_keys import trusted_key

        await redis.delete(trusted_key(message.chat.id, target_user_id))
    except Exception:
        pass
    await message.reply(f"Удалено из whitelist: {removed} записей для user_id={target_user_id}.")


@admin_router.message(Command("settings"))
async def cmd_settings(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    repo = ChatSettingsRepo()
    await repo.ensure_chat(db, chat_id=message.chat.id, title=message.chat.title)
    s = await repo.get(db, chat_id=message.chat.id)
    # Backward compatibility: migrate per-chat DB words into global file store.
    BadwordsStore.merge(set(s.bad_keywords or []))
    badwords = sorted(BadwordsStore.load_set())
    domains = list(s.allowed_domains or [])
    badwords_preview = ", ".join(badwords[:20]) if badwords else "-"
    domains_preview = ", ".join(domains[:20]) if domains else "-"
    await message.reply(
        "Текущие настройки:\n"
        f"- enabled: {s.enabled}\n"
        f"- mode: {s.mode}\n"
        f"- confirm_timeout_sec: {s.confirm_timeout_sec}\n"
        f"- timeout_action: {s.timeout_action}\n"
        f"- whitelist_after_confirm: {s.whitelist_after_confirm} ({s.whitelist_ttl_sec}s)\n"
        f"- anti_flood: {s.anti_flood_enabled} (win={s.flood_window_sec}s, max={s.flood_max_messages}, mute={s.flood_mute_sec}s)\n"
        f"- allowed_domains: {len(domains)}\n"
        f"  {domains_preview}\n"
        f"- bad_keywords: {len(badwords)}\n"
        f"  {badwords_preview}\n"
        ,
        reply_markup=settings_keyboard(
            bot.token,
            chat_id=message.chat.id,
            actor_user_id=message.from_user.id,
            enabled=bool(s.enabled),
            mode=str(s.mode),
            timeout_action=str(s.timeout_action),
        ),
    )


@admin_router.message(Command("audit"))
async def cmd_audit(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    items = await AuditRepo().last_audit(db, chat_id=message.chat.id, limit=10)
    if not items:
        await message.reply("Аудит пуст.")
        return
    lines = ["Последние действия:"]
    for it in items:
        lines.append(f"- {it.created_at:%Y-%m-%d %H:%M:%S} {it.action} {it.payload}")
    await message.reply("\n".join(lines))


@admin_router.message(Command("stats"))
async def cmd_stats(message: Message, bot: Bot, db: AsyncSession) -> None:
    if not await _require_admin(message, bot):
        return
    stats = await StatsRepo().chat_stats(db, chat_id=message.chat.id, days=1)
    await message.reply(
        "Статистика за 24 часа:\n"
        f"- проверено: {stats['analyzed']}\n"
        f"- удалено: {stats['deleted']}\n"
        f"- забанено: {stats['banned']}\n"
        f"- подтверждено: {stats['confirmed']}\n"
        f"- истекло (таймаут): {stats['expired']}\n"
    )

