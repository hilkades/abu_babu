from __future__ import annotations


def verif_key(chat_id: int, message_id: int) -> str:
    return f"verif:sess:{chat_id}:{message_id}"


def verif_due_zset() -> str:
    return "verif:due"


def flood_key(chat_id: int, user_id: int) -> str:
    return f"flood:{chat_id}:{user_id}"


def trusted_key(chat_id: int, user_id: int) -> str:
    return f"trust:{chat_id}:{user_id}"

