"""add douyin platform extensions

Revision ID: 0002_douyin_platform_extensions
Revises: 0001_initial
Create Date: 2026-06-07 14:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_douyin_platform_extensions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_ai_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_reply_mode", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_ai_setting"),
    )
    op.create_table(
        "douyin_apps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("client_key", sa.String(length=120), nullable=False),
        sa.Column("encrypted_client_secret", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "client_key", name="uq_tenant_douyin_client_key"),
    )
    op.create_table(
        "douyin_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("app_id", sa.String(length=36), sa.ForeignKey("douyin_apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("open_id", sa.String(length=128), nullable=False),
        sa.Column("nickname", sa.String(length=120), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "open_id", name="uq_tenant_douyin_open_id"),
    )
    op.create_table(
        "douyin_oauth_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("app_id", sa.String(length=36), sa.ForeignKey("douyin_apps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False, unique=True),
        sa.Column("redirect_path", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "douyin_targets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("douyin_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("poll_interval", sa.Integer(), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "item_id", name="uq_target_tenant_douyin_item_id"),
    )
    op.create_table(
        "douyin_comments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", sa.String(length=36), sa.ForeignKey("douyin_targets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("douyin_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comment_id", sa.String(length=128), nullable=False),
        sa.Column("parent_comment_id", sa.String(length=128), nullable=True),
        sa.Column("user_open_id", sa.String(length=128), nullable=True),
        sa.Column("user_nickname", sa.String(length=120), nullable=False),
        sa.Column("user_avatar_url", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("digg_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reply_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_top_level", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_handled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_replied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("target_id", "comment_id", name="uq_target_douyin_comment_id"),
    )
    op.create_table(
        "douyin_reply_actions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("douyin_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comment_id", sa.String(length=36), sa.ForeignKey("douyin_comments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operator_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "douyin_personal_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nickname", sa.String(length=120), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("external_user_id", sa.String(length=128), nullable=False),
        sa.Column("encrypted_cookie_payload", sa.Text(), nullable=False),
        sa.Column("encrypted_runtime_payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "external_user_id", name="uq_tenant_douyin_personal_user_id"),
    )
    op.create_table(
        "douyin_personal_login_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("helper_session_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("login_url", sa.String(length=1000), nullable=True),
        sa.Column("qr_image_base64", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("douyin_personal_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "douyin_personal_targets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("douyin_personal_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("aweme_id", sa.String(length=128), nullable=False),
        sa.Column("video_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("poll_interval", sa.Integer(), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "aweme_id", name="uq_target_tenant_douyin_personal_aweme_id"),
    )
    op.create_table(
        "douyin_personal_comments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", sa.String(length=36), sa.ForeignKey("douyin_personal_targets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("douyin_personal_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comment_id", sa.String(length=128), nullable=False),
        sa.Column("parent_comment_id", sa.String(length=128), nullable=True),
        sa.Column("user_external_id", sa.String(length=128), nullable=True),
        sa.Column("user_nickname", sa.String(length=120), nullable=False),
        sa.Column("user_avatar_url", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("digg_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reply_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_top_level", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_handled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_replied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("target_id", "comment_id", name="uq_target_douyin_personal_comment_id"),
    )
    op.create_table(
        "douyin_personal_reply_actions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("douyin_personal_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comment_id", sa.String(length=36), sa.ForeignKey("douyin_personal_comments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operator_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("douyin_personal_reply_actions")
    op.drop_table("douyin_personal_comments")
    op.drop_table("douyin_personal_targets")
    op.drop_table("douyin_personal_login_sessions")
    op.drop_table("douyin_personal_accounts")
    op.drop_table("douyin_reply_actions")
    op.drop_table("douyin_comments")
    op.drop_table("douyin_targets")
    op.drop_table("douyin_oauth_sessions")
    op.drop_table("douyin_accounts")
    op.drop_table("douyin_apps")
    op.drop_table("tenant_ai_settings")
