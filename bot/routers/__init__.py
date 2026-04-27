from __future__ import annotations

from aiogram import Dispatcher

from .admin import admin_router
from .callbacks import callbacks_router
from .events import events_router
from .user import user_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(callbacks_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(events_router)

