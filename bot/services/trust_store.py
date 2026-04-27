from __future__ import annotations

from redis.asyncio import Redis

from bot.services.redis_keys import trusted_key


class TrustStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def is_trusted(self, *, chat_id: int, user_id: int) -> bool:
        return bool(await self._redis.exists(trusted_key(chat_id, user_id)))

    async def trust(self, *, chat_id: int, user_id: int, ttl_sec: int) -> None:
        await self._redis.set(trusted_key(chat_id, user_id), b"1", ex=ttl_sec)

