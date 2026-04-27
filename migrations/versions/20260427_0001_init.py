"""init schema

Revision ID: 20260427_0001
Revises: None
Create Date: 2026-04-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260427_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chats",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "chat_settings",
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("confirm_timeout_sec", sa.Integer(), nullable=False),
        sa.Column("timeout_action", sa.String(length=16), nullable=False),
        sa.Column("whitelist_after_confirm", sa.Boolean(), nullable=False),
        sa.Column("whitelist_ttl_sec", sa.Integer(), nullable=False),
        sa.Column("auto_delete_links", sa.Boolean(), nullable=False),
        sa.Column("auto_delete_suspicious_media", sa.Boolean(), nullable=False),
        sa.Column("check_new_members", sa.Boolean(), nullable=False),
        sa.Column("anti_flood_enabled", sa.Boolean(), nullable=False),
        sa.Column("flood_window_sec", sa.Integer(), nullable=False),
        sa.Column("flood_max_messages", sa.Integer(), nullable=False),
        sa.Column("flood_mute_sec", sa.Integer(), nullable=False),
        sa.Column("allowed_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bad_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_whitelist",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_whitelist_chat_user"),
    )
    op.create_index("ix_whitelist_chat_expires", "user_whitelist", ["chat_id", "expires_at"])

    op.create_table(
        "suspicious_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("text_preview", sa.String(length=512), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chat_id", "message_id", name="uq_suspicious_chat_message"),
    )
    op.create_index("ix_suspicious_chat_user_created", "suspicious_messages", ["chat_id", "user_id", "created_at"])

    op.create_table(
        "verification_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("prompt_message_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chat_id", "message_id", name="uq_verif_chat_message"),
    )
    op.create_index("ix_verif_chat_user_status", "verification_sessions", ["chat_id", "user_id", "status"])
    op.create_index("ix_verif_expires_status", "verification_sessions", ["expires_at", "status"])

    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mod_actions_chat_created", "moderation_actions", ["chat_id", "created_at"])

    op.create_table(
        "spam_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_spam_events_chat_created", "spam_events", ["chat_id", "created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_chat_created", "audit_logs", ["chat_id", "created_at"])

    op.create_table(
        "domain_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("is_allowed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chat_id", "domain", name="uq_domain_chat_domain"),
    )
    op.create_index("ix_domain_chat_allowed", "domain_rules", ["chat_id", "is_allowed"])

    op.create_table(
        "keyword_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("keyword", sa.String(length=128), nullable=False),
        sa.Column("is_bad", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chat_id", "keyword", name="uq_keyword_chat_keyword"),
    )
    op.create_index("ix_keyword_chat_is_bad", "keyword_rules", ["chat_id", "is_bad"])

    op.create_table(
        "flood_rules",
        sa.Column("chat_id", sa.BigInteger(), primary_key=True),
        sa.Column("window_sec", sa.Integer(), nullable=False),
        sa.Column("max_messages", sa.Integer(), nullable=False),
        sa.Column("mute_sec", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("flood_rules")
    op.drop_index("ix_keyword_chat_is_bad", table_name="keyword_rules")
    op.drop_table("keyword_rules")
    op.drop_index("ix_domain_chat_allowed", table_name="domain_rules")
    op.drop_table("domain_rules")
    op.drop_index("ix_audit_chat_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_spam_events_chat_created", table_name="spam_events")
    op.drop_table("spam_events")
    op.drop_index("ix_mod_actions_chat_created", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_index("ix_verif_expires_status", table_name="verification_sessions")
    op.drop_index("ix_verif_chat_user_status", table_name="verification_sessions")
    op.drop_table("verification_sessions")
    op.drop_index("ix_suspicious_chat_user_created", table_name="suspicious_messages")
    op.drop_table("suspicious_messages")
    op.drop_index("ix_whitelist_chat_expires", table_name="user_whitelist")
    op.drop_table("user_whitelist")
    op.drop_table("chat_settings")
    op.drop_table("users")
    op.drop_table("chats")

