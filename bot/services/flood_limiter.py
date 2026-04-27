from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis

from bot.services.redis_keys import flood_key


@dataclass(frozen=True)
class FloodCheckResult:
    allowed: bool
    count: int


LUA_FLOOD = r"""
-- KEYS[1] = flood list key
-- ARGV = now_ms, window_ms, max_count, ttl_sec
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_count = tonumber(ARGV[3])

redis.call("LPUSH", KEYS[1], tostring(now))
redis.call("LTRIM", KEYS[1], 0, max_count * 2) -- small cap
redis.call("EXPIRE", KEYS[1], tonumber(ARGV[4]))

local items = redis.call("LRANGE", KEYS[1], 0, -1)
local cnt = 0
for i=1,#items do
  local ts = tonumber(items[i])
  if ts ~= nil and (now - ts) <= window then
    cnt = cnt + 1
  end
end

if cnt > max_count then
  return {0, cnt}
end
return {1, cnt}
"""


class FloodLimiter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check(
        self,
        *,
        chat_id: int,
        user_id: int,
        now_ms: int,
        window_sec: int,
        max_messages: int,
    ) -> FloodCheckResult:
        key = flood_key(chat_id, user_id)
        window_ms = window_sec * 1000
        ttl_sec = max(window_sec * 2, 5)
        allowed_i, count = await self._redis.eval(
            LUA_FLOOD, 1, key, str(now_ms), str(window_ms), str(max_messages), str(ttl_sec)
        )
        return FloodCheckResult(allowed=bool(int(allowed_i)), count=int(count))

