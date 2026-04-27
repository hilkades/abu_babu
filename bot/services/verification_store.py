from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from bot.services.redis_keys import verif_due_zset, verif_key
from bot.utils.crypto import sha256_hex


@dataclass(frozen=True)
class CreateVerificationResult:
    created: bool
    expires_at: int


@dataclass(frozen=True)
class ConfirmResult:
    ok: bool
    reason: str  # "ok" | "not_found" | "expired" | "wrong_user" | "wrong_token" | "already"


@dataclass(frozen=True)
class SessionSnapshot:
    chat_id: int
    message_id: int
    user_id: int
    status: str
    expires_at: int


LUA_CREATE = r"""
-- KEYS[1] = session hash key
-- KEYS[2] = due zset
-- ARGV = chat_id, message_id, user_id, token_hash, expires_at, ttl_sec
local exists = redis.call("EXISTS", KEYS[1])
if exists == 1 then
  return {0, redis.call("HGET", KEYS[1], "expires_at")}
end
redis.call("HSET", KEYS[1],
  "chat_id", ARGV[1],
  "message_id", ARGV[2],
  "user_id", ARGV[3],
  "token_hash", ARGV[4],
  "status", "waiting",
  "expires_at", ARGV[5]
)
redis.call("EXPIRE", KEYS[1], tonumber(ARGV[6]))
redis.call("ZADD", KEYS[2], tonumber(ARGV[5]), ARGV[1] .. ":" .. ARGV[2])
return {1, ARGV[5]}
"""


LUA_CONFIRM = r"""
-- KEYS[1] = session hash key
-- ARGV = user_id, token_hash, now_ts
if redis.call("EXISTS", KEYS[1]) == 0 then
  return "not_found"
end
local status = redis.call("HGET", KEYS[1], "status")
if status == "confirmed" then
  return "already"
end
if status == "expired" then
  return "expired"
end
local expires_at = tonumber(redis.call("HGET", KEYS[1], "expires_at"))
if expires_at ~= nil and expires_at <= tonumber(ARGV[3]) then
  redis.call("HSET", KEYS[1], "status", "expired")
  return "expired"
end
local user_id = redis.call("HGET", KEYS[1], "user_id")
if user_id ~= ARGV[1] then
  return "wrong_user"
end
local token_hash = redis.call("HGET", KEYS[1], "token_hash")
if token_hash ~= ARGV[2] then
  return "wrong_token"
end
redis.call("HSET", KEYS[1], "status", "confirmed")
return "ok"
"""


LUA_EXPIRE_MARK = r"""
-- KEYS[1] = session hash key
-- ARGV = now_ts
if redis.call("EXISTS", KEYS[1]) == 0 then
  return "not_found"
end
local status = redis.call("HGET", KEYS[1], "status")
if status ~= "waiting" then
  return status
end
local expires_at = tonumber(redis.call("HGET", KEYS[1], "expires_at"))
if expires_at ~= nil and expires_at <= tonumber(ARGV[1]) then
  redis.call("HSET", KEYS[1], "status", "expired")
  return "expired"
end
return "waiting"
"""


class VerificationStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def create_if_absent(
        self,
        *,
        chat_id: int,
        message_id: int,
        user_id: int,
        token_plain: str,
        expires_at: int,
        ttl_sec: int,
    ) -> CreateVerificationResult:
        token_hash = sha256_hex(token_plain.encode("utf-8"))
        key = verif_key(chat_id, message_id)
        due = verif_due_zset()
        res: list[Any] = await self._redis.eval(
            LUA_CREATE,
            2,
            key,
            due,
            str(chat_id),
            str(message_id),
            str(user_id),
            token_hash,
            str(expires_at),
            str(ttl_sec),
        )
        created = bool(int(res[0]))
        exp = int(res[1])
        return CreateVerificationResult(created=created, expires_at=exp)

    async def confirm(
        self, *, chat_id: int, message_id: int, user_id: int, token_plain: str, now_ts: int
    ) -> ConfirmResult:
        key = verif_key(chat_id, message_id)
        token_hash = sha256_hex(token_plain.encode("utf-8"))
        raw = await self._redis.eval(LUA_CONFIRM, 1, key, str(user_id), token_hash, str(now_ts))
        if isinstance(raw, (bytes, bytearray)):
            reason = raw.decode("utf-8", errors="replace")
        else:
            reason = str(raw)
        return ConfirmResult(ok=(reason == "ok"), reason=reason)

    async def mark_expired_if_due(self, *, chat_id: int, message_id: int, now_ts: int) -> str:
        key = verif_key(chat_id, message_id)
        raw = await self._redis.eval(LUA_EXPIRE_MARK, 1, key, str(now_ts))
        if isinstance(raw, (bytes, bytearray)):
            return raw.decode("utf-8", errors="replace")
        return str(raw)

    async def get_snapshot(self, *, chat_id: int, message_id: int) -> SessionSnapshot | None:
        key = verif_key(chat_id, message_id)
        data = await self._redis.hgetall(key)
        if not data:
            return None
        try:
            return SessionSnapshot(
                chat_id=int((data.get(b"chat_id") or b"0").decode("utf-8")),
                message_id=int((data.get(b"message_id") or b"0").decode("utf-8")),
                user_id=int((data.get(b"user_id") or b"0").decode("utf-8")),
                status=(data.get(b"status") or b"").decode("utf-8"),
                expires_at=int((data.get(b"expires_at") or b"0").decode("utf-8")),
            )
        except Exception:
            return None

    async def pop_due(self, *, now_ts: int, limit: int = 200) -> list[tuple[int, int]]:
        """
        Возвращает [(chat_id, message_id), ...] для сессий, у которых expires_at <= now_ts.
        Удаляет их из ZSET, чтобы не обрабатывать повторно.
        """
        due_key = verif_due_zset()
        members: list[bytes] = await self._redis.zrangebyscore(due_key, min="-inf", max=str(now_ts), start=0, num=limit)
        if not members:
            return []
        pipe = self._redis.pipeline(transaction=True)
        for m in members:
            pipe.zrem(due_key, m)
        await pipe.execute()
        out: list[tuple[int, int]] = []
        for m in members:
            try:
                chat_s, msg_s = m.decode("utf-8").split(":", 1)
                out.append((int(chat_s), int(msg_s)))
            except Exception:
                continue
        return out

