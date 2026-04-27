from __future__ import annotations

from bot.antispam.scorer import score_message
from bot.antispam.types import MessageFeatures
from bot.models.enums import RiskLevel, StrictnessMode


def test_safe_text_is_safe() -> None:
    f = MessageFeatures(text="Привет! Как дела?")
    r = score_message(f, mode=StrictnessMode.balanced)
    assert r.risk_level == RiskLevel.safe


def test_invite_link_is_at_least_suspicious() -> None:
    f = MessageFeatures(text="Join https://t.me/+abcdef")
    r = score_message(f, mode=StrictnessMode.balanced)
    assert r.score > 0
    assert r.risk_level in {RiskLevel.suspicious, RiskLevel.spam, RiskLevel.critical}


def test_short_text_with_url_scores_high() -> None:
    f = MessageFeatures(text="Go https://bit.ly/x", urls=["https://bit.ly/x"], domains=["bit.ly"])
    r = score_message(f, mode=StrictnessMode.strict)
    assert r.reasons.get("shortener", 0) > 0
    assert r.reasons.get("text_very_short_with_url", 0) > 0
    assert r.risk_level in {RiskLevel.suspicious, RiskLevel.spam, RiskLevel.critical}

