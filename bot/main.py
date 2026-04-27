from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from bot.background import verification_timeout_loop
from bot.config import load_settings
from bot.db import create_engine, create_sessionmaker
from bot.middlewares import DbSessionMiddleware, RedisMiddleware
from bot.redis import create_redis
from bot.routers import setup_routers
from bot.utils.logging import configure_logging, get_logger


async def main() -> None:
    settings = load_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    log = get_logger("boot")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    engine = create_engine(settings.postgres_dsn)
    sm = create_sessionmaker(engine)
    redis = create_redis(settings.redis_dsn)

    dp.update.middleware(DbSessionMiddleware(sm))
    dp.update.middleware(RedisMiddleware(redis))

    setup_routers(dp)

    log.info("starting_bot")
    try:
        timeout_task = asyncio.create_task(
            verification_timeout_loop(bot=bot, redis=redis, sessionmaker=sm),
            name="verification_timeout_loop",
        )
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        try:
            timeout_task.cancel()
        except Exception:
            pass
        try:
            await timeout_task
        except Exception:
            pass
        await bot.session.close()
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

