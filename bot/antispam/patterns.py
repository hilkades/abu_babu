from __future__ import annotations

import re


URL_RE = re.compile(r"(?i)\bhttps?://[^\s<>()]+")
DOMAIN_RE = re.compile(r"(?i)^(?:https?://)?(?:www\.)?([^/:?#]+)")

INVITE_RE = re.compile(r"(?i)\b(t\.me/joinchat/|t\.me/\+|telegram\.me/joinchat/)")

# very common URL shorteners
SHORTENER_DOMAINS = {
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "is.gd",
    "cutt.ly",
    "rebrand.ly",
    "shorturl.at",
    "ow.ly",
}

# “casino/crypto/adult/scam/phish” seed keywords; per-chat rules extend this
BAD_KEYWORDS_BASE = {
    "casino",
    "bet",
    "bonus",
    "crypto",
    "airdrop",
    "usdt",
    "btc",
    "eth",
    "binance",
    "wallet",
    "profit",
    "invest",
    "scam",
    "phish",
    "porn",
    "adult",
    "sex",
    "onlyfans",
    "win",
    "jackpot",
    "free money",
    "giveaway",
    "support",
    "write me",
    "dm me",
    "pm me",
}

REPEATED_CHAR_RE = re.compile(r"(.)\1{6,}")
MANY_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF]")

