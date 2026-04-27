from __future__ import annotations

from redis.asyncio import Redis


def create_redis(dsn: str) -> Redis:
    # decode_responses=False: храним bytes, чтобы избежать неожиданных преобразований
    return Redis.from_url(dsn, decode_responses=False)

