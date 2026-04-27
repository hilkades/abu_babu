from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db import Base
from bot.models.enums import ModerationActionType, RiskLevel, StrictnessMode, TimeoutAction, VerificationStatus


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram chat_id
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    settings: Mapped["ChatSettings"] = relationship(back_populates="chat", uselist=False)


class ChatSettings(Base):
    __tablename__ = "chat_settings"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    mode: Mapped[str] = mapped_column(String(16), default=StrictnessMode.balanced.value)

    confirm_timeout_sec: Mapped[int] = mapped_column(Integer, default=90)
    timeout_action: Mapped[str] = mapped_column(String(16), default=TimeoutAction.delete.value)
    whitelist_after_confirm: Mapped[bool] = mapped_column(Boolean, default=True)
    whitelist_ttl_sec: Mapped[int] = mapped_column(Integer, default=24 * 3600)

    auto_delete_links: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_delete_suspicious_media: Mapped[bool] = mapped_column(Boolean, default=True)
    check_new_members: Mapped[bool] = mapped_column(Boolean, default=True)

    anti_flood_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    flood_window_sec: Mapped[int] = mapped_column(Integer, default=10)
    flood_max_messages: Mapped[int] = mapped_column(Integer, default=6)
    flood_mute_sec: Mapped[int] = mapped_column(Integer, default=120)

    allowed_domains: Mapped[list[str]] = mapped_column(JSONB, default=list)
    bad_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)

    thresholds: Mapped[dict] = mapped_column(JSONB, default=dict)  # risk score thresholds per mode
    weights: Mapped[dict] = mapped_column(JSONB, default=dict)  # scoring weights per mode

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    chat: Mapped[Chat] = relationship(back_populates="settings")


class TgUser(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram user_id
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserWhitelist(Base):
    __tablename__ = "user_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_whitelist_chat_user"),
        Index("ix_whitelist_chat_expires", "chat_id", "expires_at"),
    )


class SuspiciousMessage(Base):
    __tablename__ = "suspicious_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    risk_level: Mapped[str] = mapped_column(String(16), default=RiskLevel.suspicious.value)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    reasons: Mapped[dict] = mapped_column(JSONB, default=dict)  # {rule: weight}

    text_preview: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)  # partial event snapshot

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("chat_id", "message_id", name="uq_suspicious_chat_message"),
        Index("ix_suspicious_chat_user_created", "chat_id", "user_id", "created_at"),
    )


class VerificationSession(Base):
    __tablename__ = "verification_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default=VerificationStatus.waiting.value)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("chat_id", "message_id", name="uq_verif_chat_message"),
        Index("ix_verif_chat_user_status", "chat_id", "user_id", "status"),
        Index("ix_verif_expires_status", "expires_at", "status"),
    )


class ModerationAction(Base):
    __tablename__ = "moderation_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    action_type: Mapped[str] = mapped_column(String(32), default=ModerationActionType.delete_message.value)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (Index("ix_mod_actions_chat_created", "chat_id", "created_at"),)


class SpamEvent(Base):
    __tablename__ = "spam_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    reasons: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (Index("ix_spam_events_chat_created", "chat_id", "created_at"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # admin id
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (Index("ix_audit_chat_created", "chat_id", "created_at"),)


class DomainRule(Base):
    __tablename__ = "domain_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("chat_id", "domain", name="uq_domain_chat_domain"),
        Index("ix_domain_chat_allowed", "chat_id", "is_allowed"),
    )


class KeywordRule(Base):
    __tablename__ = "keyword_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    keyword: Mapped[str] = mapped_column(String(128), nullable=False)
    is_bad: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("chat_id", "keyword", name="uq_keyword_chat_keyword"),
        Index("ix_keyword_chat_is_bad", "chat_id", "is_bad"),
    )


class FloodRule(Base):
    __tablename__ = "flood_rules"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    window_sec: Mapped[int] = mapped_column(Integer, default=10)
    max_messages: Mapped[int] = mapped_column(Integer, default=6)
    mute_sec: Mapped[int] = mapped_column(Integer, default=120)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

