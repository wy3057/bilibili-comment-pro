from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class AccountStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    disabled = "disabled"


class RiskStatus(str, enum.Enum):
    normal = "normal"
    warning = "warning"
    limited = "limited"


class TargetStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class DraftStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    sent = "sent"


class AIReplyMode(str, enum.Enum):
    manual_review = "manual_review"
    direct_send = "direct_send"


class IntegrationType(str, enum.Enum):
    enterprise = "enterprise"
    personal = "personal"


class ReplyActionStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class CommentEventType(str, enum.Enum):
    discovered = "discovered"
    updated = "updated"
    deleted = "deleted"
    hydrated = "hydrated"


class TaskKind(str, enum.Enum):
    poll_comments = "poll_comments"
    refresh_credentials = "refresh_credentials"
    sync_targets = "sync_targets"
    notify = "notify"


class TaskStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class Tenant(Base, IdMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    members: Mapped[list["TenantMember"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    accounts: Mapped[list["BilibiliAccount"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    douyin_apps: Mapped[list["DouyinApp"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    douyin_accounts: Mapped[list["DouyinAccount"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    douyin_personal_accounts: Mapped[list["DouyinPersonalAccount"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    targets: Mapped[list["MonitorTarget"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    douyin_targets: Mapped[list["DouyinTarget"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    douyin_personal_targets: Mapped[list["DouyinPersonalTarget"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    memberships: Mapped[list["TenantMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class TenantMember(Base, IdMixin, TimestampMixin):
    __tablename__ = "tenant_members"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_member"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default=UserRole.viewer.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")


class RefreshToken(Base, IdMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship()


class BilibiliAccount(Base, IdMixin, TimestampMixin):
    __tablename__ = "bilibili_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "uid", name="uq_tenant_bili_uid"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    uid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[AccountStatus] = mapped_column(String(20), default=AccountStatus.active.value, nullable=False)
    risk_status: Mapped[RiskStatus] = mapped_column(String(20), default=RiskStatus.normal.value, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="accounts")
    credential: Mapped[Optional["BilibiliCredential"]] = relationship(
        back_populates="account", cascade="all, delete-orphan", uselist=False
    )


class BilibiliCredential(Base, IdMixin, TimestampMixin):
    __tablename__ = "bilibili_credentials"

    account_id: Mapped[str] = mapped_column(
        ForeignKey("bilibili_accounts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped["BilibiliAccount"] = relationship(back_populates="credential")


class DouyinApp(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_apps"
    __table_args__ = (UniqueConstraint("tenant_id", "client_key", name="uq_tenant_douyin_client_key"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    client_key: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_client_secret: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="douyin_apps")
    accounts: Mapped[list["DouyinAccount"]] = relationship(back_populates="app", cascade="all, delete-orphan")


class DouyinAccount(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "open_id", name="uq_tenant_douyin_open_id"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    app_id: Mapped[str] = mapped_column(ForeignKey("douyin_apps.id", ondelete="CASCADE"), nullable=False)
    open_id: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AccountStatus] = mapped_column(String(20), default=AccountStatus.active.value, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="douyin_accounts")
    app: Mapped["DouyinApp"] = relationship(back_populates="accounts")


class DouyinOAuthSession(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_oauth_sessions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    app_id: Mapped[str] = mapped_column(ForeignKey("douyin_apps.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    redirect_path: Mapped[str] = mapped_column(String(500), nullable=False, default="/ops?tab=accounts&platform=douyin")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")


class DouyinTarget(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_targets"
    __table_args__ = (UniqueConstraint("tenant_id", "item_id", name="uq_target_tenant_douyin_item_id"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("douyin_accounts.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TargetStatus] = mapped_column(String(20), default=TargetStatus.active.value, nullable=False)
    poll_interval: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="douyin_targets")
    account: Mapped["DouyinAccount"] = relationship()
    comments: Mapped[list["DouyinComment"]] = relationship(back_populates="target", cascade="all, delete-orphan")


class DouyinPersonalAccount(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_personal_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "external_user_id", name="uq_tenant_douyin_personal_user_id"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    nickname: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    external_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_cookie_payload: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_runtime_payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AccountStatus] = mapped_column(String(20), default=AccountStatus.active.value, nullable=False)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="douyin_personal_accounts")
    targets: Mapped[list["DouyinPersonalTarget"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class DouyinPersonalLoginSession(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_personal_login_sessions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    helper_session_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    login_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    qr_image_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    account_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("douyin_personal_accounts.id", ondelete="SET NULL"), nullable=True
    )


class DouyinPersonalTarget(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_personal_targets"
    __table_args__ = (UniqueConstraint("tenant_id", "aweme_id", name="uq_target_tenant_douyin_personal_aweme_id"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("douyin_personal_accounts.id", ondelete="CASCADE"), nullable=False
    )
    aweme_id: Mapped[str] = mapped_column(String(128), nullable=False)
    video_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TargetStatus] = mapped_column(String(20), default=TargetStatus.active.value, nullable=False)
    poll_interval: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="douyin_personal_targets")
    account: Mapped["DouyinPersonalAccount"] = relationship(back_populates="targets")
    comments: Mapped[list["DouyinPersonalComment"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )


class TenantWebhookConfig(Base, IdMixin, TimestampMixin):
    __tablename__ = "tenant_webhook_configs"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TenantAISetting(Base, IdMixin, TimestampMixin):
    __tablename__ = "tenant_ai_settings"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_ai_setting"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    ai_reply_mode: Mapped[AIReplyMode] = mapped_column(
        String(30), default=AIReplyMode.manual_review.value, nullable=False
    )


class MonitorTarget(Base, IdMixin, TimestampMixin):
    __tablename__ = "monitor_targets"
    __table_args__ = (UniqueConstraint("tenant_id", "bvid", name="uq_target_tenant_bvid"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("bilibili_accounts.id", ondelete="CASCADE"), nullable=False)
    oid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bvid: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_mid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[TargetStatus] = mapped_column(String(20), default=TargetStatus.active.value, nullable=False)
    poll_interval: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="targets")
    account: Mapped["BilibiliAccount"] = relationship()
    comments: Mapped[list["Comment"]] = relationship(back_populates="target", cascade="all, delete-orphan")


class Comment(Base, IdMixin, TimestampMixin):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("target_id", "rpid", name="uq_target_comment_rpid"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str] = mapped_column(ForeignKey("monitor_targets.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("bilibili_accounts.id", ondelete="CASCADE"), nullable=False)
    rpid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    root_rpid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    parent_rpid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    oid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    member_mid: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    member_name: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_top_level: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_replied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    target: Mapped["MonitorTarget"] = relationship(back_populates="comments")
    events: Mapped[list["CommentEvent"]] = relationship(back_populates="comment", cascade="all, delete-orphan")


class CommentEvent(Base, IdMixin, TimestampMixin):
    __tablename__ = "comment_events"

    comment_id: Mapped[str] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[CommentEventType] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    comment: Mapped["Comment"] = relationship(back_populates="events")


class ReplyDraft(Base, IdMixin, TimestampMixin):
    __tablename__ = "reply_drafts"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[str] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    operator_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(String(20), default=DraftStatus.draft.value, nullable=False)


class ReplyAction(Base, IdMixin, TimestampMixin):
    __tablename__ = "reply_actions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("bilibili_accounts.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[str] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    draft_id: Mapped[Optional[str]] = mapped_column(ForeignKey("reply_drafts.id", ondelete="SET NULL"), nullable=True)
    operator_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[ReplyActionStatus] = mapped_column(
        String(20), default=ReplyActionStatus.pending.value, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DouyinComment(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_comments"
    __table_args__ = (UniqueConstraint("target_id", "comment_id", name="uq_target_douyin_comment_id"),)

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str] = mapped_column(ForeignKey("douyin_targets.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("douyin_accounts.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    user_open_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    user_nickname: Mapped[str] = mapped_column(String(120), nullable=False)
    user_avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    digg_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_top_level: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_replied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    target: Mapped["DouyinTarget"] = relationship(back_populates="comments")


class DouyinReplyAction(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_reply_actions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("douyin_accounts.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[str] = mapped_column(ForeignKey("douyin_comments.id", ondelete="CASCADE"), nullable=False)
    operator_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[ReplyActionStatus] = mapped_column(
        String(20), default=ReplyActionStatus.pending.value, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DouyinPersonalComment(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_personal_comments"
    __table_args__ = (
        UniqueConstraint("target_id", "comment_id", name="uq_target_douyin_personal_comment_id"),
    )

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str] = mapped_column(
        ForeignKey("douyin_personal_targets.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("douyin_personal_accounts.id", ondelete="CASCADE"), nullable=False
    )
    comment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_comment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    user_external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    user_nickname: Mapped[str] = mapped_column(String(120), nullable=False)
    user_avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    digg_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_top_level: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_replied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    target: Mapped["DouyinPersonalTarget"] = relationship(back_populates="comments")


class DouyinPersonalReplyAction(Base, IdMixin, TimestampMixin):
    __tablename__ = "douyin_personal_reply_actions"

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("douyin_personal_accounts.id", ondelete="CASCADE"), nullable=False
    )
    comment_id: Mapped[str] = mapped_column(
        ForeignKey("douyin_personal_comments.id", ondelete="CASCADE"), nullable=False
    )
    operator_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[ReplyActionStatus] = mapped_column(
        String(20), default=ReplyActionStatus.pending.value, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base, IdMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    tenant_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class TaskRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "task_runs"

    tenant_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    account_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("bilibili_accounts.id", ondelete="SET NULL"), nullable=True
    )
    target_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("monitor_targets.id", ondelete="SET NULL"), nullable=True
    )
    task_name: Mapped[str] = mapped_column(String(120), nullable=False)
    task_kind: Mapped[TaskKind] = mapped_column(String(30), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
