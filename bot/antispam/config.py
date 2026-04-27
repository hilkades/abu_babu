from __future__ import annotations

from bot.models.enums import StrictnessMode


DEFAULT_THRESHOLDS: dict[str, dict[str, int]] = {
    "strict": {"suspicious": 20, "spam": 35, "critical": 55},
    "balanced": {"suspicious": 25, "spam": 45, "critical": 70},
    "lenient": {"suspicious": 35, "spam": 60, "critical": 90},
}


DEFAULT_WEIGHTS: dict[str, dict[str, int]] = {
    # Higher is worse
    "strict": {
        "has_url": 12,
        "invite_link": 25,
        "shortener": 18,
        "bad_keyword": 18,
        "caps_ratio_high": 8,
        "emoji_many": 8,
        "repeated_chars": 10,
        "text_too_long": 6,
        "text_very_short_with_url": 14,
        "forwarded": 6,
        "media_with_ad_caption": 14,
        "domain_not_allowed": 16,
    },
    "balanced": {
        "has_url": 10,
        "invite_link": 22,
        "shortener": 16,
        "bad_keyword": 16,
        "caps_ratio_high": 7,
        "emoji_many": 7,
        "repeated_chars": 9,
        "text_too_long": 5,
        "text_very_short_with_url": 12,
        "forwarded": 5,
        "media_with_ad_caption": 12,
        "domain_not_allowed": 14,
    },
    "lenient": {
        "has_url": 8,
        "invite_link": 20,
        "shortener": 14,
        "bad_keyword": 14,
        "caps_ratio_high": 6,
        "emoji_many": 6,
        "repeated_chars": 8,
        "text_too_long": 4,
        "text_very_short_with_url": 10,
        "forwarded": 4,
        "media_with_ad_caption": 10,
        "domain_not_allowed": 12,
    },
}


def normalize_mode(mode: str) -> StrictnessMode:
    try:
        return StrictnessMode(mode)
    except Exception:
        return StrictnessMode.balanced

