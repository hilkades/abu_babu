from __future__ import annotations

from dataclasses import dataclass, field

from bot.models.enums import RiskLevel, StrictnessMode


@dataclass(frozen=True)
class ScoringConfig:
    mode: StrictnessMode
    weights: dict[str, int]
    thresholds: dict[str, int]  # suspicious/spam/critical boundaries


@dataclass(frozen=True)
class MessageFeatures:
    text: str
    urls: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    has_forward: bool = False
    has_media: bool = False
    is_new_member: bool = False


@dataclass(frozen=True)
class AnalysisResult:
    risk_level: RiskLevel
    score: int
    reasons: dict[str, int]
    features: MessageFeatures

