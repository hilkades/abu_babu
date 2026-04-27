from __future__ import annotations

import enum


class StrictnessMode(str, enum.Enum):
    strict = "strict"
    balanced = "balanced"
    lenient = "lenient"


class TimeoutAction(str, enum.Enum):
    delete = "delete"
    mute = "mute"
    kick = "kick"
    ban = "ban"


class RiskLevel(str, enum.Enum):
    safe = "safe"
    suspicious = "suspicious"
    spam = "spam"
    critical = "critical"


class VerificationStatus(str, enum.Enum):
    waiting = "waiting"
    confirmed = "confirmed"
    expired = "expired"
    cancelled = "cancelled"


class ModerationActionType(str, enum.Enum):
    delete_message = "delete_message"
    restrict_user = "restrict_user"
    kick_user = "kick_user"
    ban_user = "ban_user"
    warn = "warn"

