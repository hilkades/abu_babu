from __future__ import annotations

from collections import Counter
import re

from bot.antispam.config import DEFAULT_THRESHOLDS, DEFAULT_WEIGHTS
from bot.antispam.patterns import (
    BAD_KEYWORDS_BASE,
    INVITE_RE,
    MANY_EMOJI_RE,
    REPEATED_CHAR_RE,
    SHORTENER_DOMAINS,
)
from bot.antispam.types import AnalysisResult, MessageFeatures
from bot.models.enums import RiskLevel, StrictnessMode


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    caps = sum(1 for c in letters if c.isupper())
    return caps / max(len(letters), 1)


def _emoji_count(text: str) -> int:
    return len(MANY_EMOJI_RE.findall(text))


def _contains_bad_keywords(
    text_cf: str,
    bad_keywords_cf: set[str],
    bad_keywords_regex: list[str] | None = None,
) -> bool:
    for kw in bad_keywords_cf:
        if kw and kw in text_cf:
            return True
    if bad_keywords_regex:
        for pattern in bad_keywords_regex:
            try:
                if re.search(pattern, text_cf, flags=re.IGNORECASE):
                    return True
            except re.error:
                # Invalid regex fallback: treat as plain text token.
                if pattern and pattern.casefold() in text_cf:
                    return True
    return False


def _looks_like_ad_caption(text_l: str) -> bool:
    markers = ("promo", "discount", "sale", "subscribe", "channel", "link", "price", "delivery")
    return any(m in text_l for m in markers)


def score_message(
    features: MessageFeatures,
    *,
    mode: StrictnessMode,
    allowed_domains: set[str] | None = None,
    extra_bad_keywords: set[str] | None = None,
    extra_bad_keywords_regex: list[str] | None = None,
    override_weights: dict[str, int] | None = None,
    override_thresholds: dict[str, int] | None = None,
) -> AnalysisResult:
    allowed_domains = allowed_domains or set()
    bad_keywords_cf = {k.casefold() for k in BAD_KEYWORDS_BASE if k}
    if extra_bad_keywords:
        bad_keywords_cf |= {k.casefold() for k in extra_bad_keywords if k}

    weights = dict(DEFAULT_WEIGHTS[mode.value])
    if override_weights:
        weights.update({k: int(v) for k, v in override_weights.items()})

    thresholds = dict(DEFAULT_THRESHOLDS[mode.value])
    if override_thresholds:
        thresholds.update({k: int(v) for k, v in override_thresholds.items()})

    text = features.text or ""
    text_cf = text.casefold()
    reasons: Counter[str] = Counter()

    if features.urls:
        reasons["has_url"] += 1
        if INVITE_RE.search(text_cf):
            reasons["invite_link"] += 1

    if any(d in SHORTENER_DOMAINS for d in features.domains):
        reasons["shortener"] += 1

    if features.domains and allowed_domains:
        for d in features.domains:
            if d not in allowed_domains and not any(d.endswith("." + a) for a in allowed_domains):
                reasons["domain_not_allowed"] += 1
                break

    if _contains_bad_keywords(text_cf, bad_keywords_cf, extra_bad_keywords_regex):
        reasons["bad_keyword"] += 1

    if _caps_ratio(text) >= 0.7 and len(text) >= 8:
        reasons["caps_ratio_high"] += 1

    if _emoji_count(text) >= 12:
        reasons["emoji_many"] += 1

    if REPEATED_CHAR_RE.search(text):
        reasons["repeated_chars"] += 1

    if len(text) >= 1200:
        reasons["text_too_long"] += 1

    if len(text) <= 10 and features.urls:
        reasons["text_very_short_with_url"] += 1

    if features.has_forward:
        reasons["forwarded"] += 1

    if features.has_media and features.text and _looks_like_ad_caption(text_cf):
        reasons["media_with_ad_caption"] += 1

    # Behavioural / repetition hooks (placeholder): can be enriched by per-user stats
    # e.g. same text repeated — injected from higher layer; keep key reserved:
    # reasons["repeated_text"] += 1

    score = 0
    scored_reasons: dict[str, int] = {}
    for rule, count in reasons.items():
        w = int(weights.get(rule, 0))
        if w <= 0:
            continue
        scored_reasons[rule] = w * int(count)
        score += scored_reasons[rule]

    if score >= thresholds["critical"]:
        level = RiskLevel.critical
    elif score >= thresholds["spam"]:
        level = RiskLevel.spam
    elif score >= thresholds["suspicious"]:
        level = RiskLevel.suspicious
    else:
        level = RiskLevel.safe

    return AnalysisResult(risk_level=level, score=score, reasons=scored_reasons, features=features)

