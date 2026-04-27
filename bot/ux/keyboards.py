from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.enums import StrictnessMode, TimeoutAction
from bot.utils.crypto import hmac_sha256_hex


def _settings_cb(bot_token: str, *, chat_id: int, actor_user_id: int, op: str) -> str:
    base = f"s1|{chat_id}|{actor_user_id}|{op}"
    sig = hmac_sha256_hex(bot_token.encode("utf-8"), base.encode("utf-8"))[:12]
    return f"{base}|{sig}"


def settings_keyboard(
    bot_token: str,
    *,
    chat_id: int,
    actor_user_id: int,
    enabled: bool,
    mode: str,
    timeout_action: str,
) -> InlineKeyboardMarkup:
    mode_v = mode
    action_v = timeout_action
    toggle_text = "Выключить" if enabled else "Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{toggle_text} антиспам",
                    callback_data=_settings_cb(bot_token, chat_id=chat_id, actor_user_id=actor_user_id, op="toggle"),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Режим: {mode_v} (сменить)",
                    callback_data=_settings_cb(bot_token, chat_id=chat_id, actor_user_id=actor_user_id, op="cycle_mode"),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Timeout action: {action_v} (сменить)",
                    callback_data=_settings_cb(bot_token, chat_id=chat_id, actor_user_id=actor_user_id, op="cycle_action"),
                )
            ],
        ]
    )

