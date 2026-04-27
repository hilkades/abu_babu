from __future__ import annotations

from aiogram.types import Message

from bot.antispam.patterns import DOMAIN_RE, URL_RE
from bot.antispam.types import MessageFeatures


def _extract_text(message: Message) -> str:
    parts: list[str] = []
    if message.text:
        parts.append(message.text)
    if message.caption:
        parts.append(message.caption)
    # Telegram API не даёт читать содержимое файлов, поэтому “текст в видео/доках” — только из caption/filename.
    if message.document and message.document.file_name:
        parts.append(message.document.file_name)
    return "\n".join(parts).strip()


def _extract_urls(text: str) -> list[str]:
    return [m.group(0) for m in URL_RE.finditer(text)]


def _extract_domains(urls: list[str]) -> list[str]:
    out: list[str] = []
    for url in urls:
        m = DOMAIN_RE.match(url)
        if not m:
            continue
        out.append(m.group(1).lower())
    return out


def extract_features(message: Message, *, is_new_member: bool = False) -> MessageFeatures:
    text = _extract_text(message)
    urls = _extract_urls(text)
    domains = _extract_domains(urls)
    has_forward = bool(message.forward_date or message.forward_origin)
    has_media = bool(
        message.photo
        or message.video
        or message.animation
        or message.document
        or message.audio
        or message.voice
        or message.video_note
    )
    return MessageFeatures(
        text=text,
        urls=urls,
        domains=domains,
        has_forward=has_forward,
        has_media=has_media,
        is_new_member=is_new_member,
    )

