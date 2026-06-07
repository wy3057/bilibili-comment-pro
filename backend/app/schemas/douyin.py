from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel, TimestampedModel


class DouyinAppCreate(BaseModel):
    name: str
    client_key: str
    client_secret: str


class DouyinAppOut(TimestampedModel):
    tenant_id: str
    name: str
    client_key: str
    is_active: bool


class DouyinAccountImport(BaseModel):
    app_id: str
    open_id: str
    access_token: str
    refresh_token: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token_expires_at: Optional[datetime] = None


class DouyinOAuthStartRequest(BaseModel):
    app_id: str
    redirect_path: str = "/ops?tab=accounts&platform=douyin"


class DouyinOAuthStartOut(BaseModel):
    session_id: str
    state: str
    auth_url: str
    expires_at: datetime


class DouyinOAuthExchangeCodeRequest(BaseModel):
    app_id: str
    code: str


class DouyinAccountOut(TimestampedModel):
    tenant_id: str
    app_id: str
    open_id: str
    nickname: str
    avatar_url: Optional[str] = None
    status: str
    access_token_expires_at: Optional[datetime] = None
    last_validated_at: Optional[datetime] = None
    last_error: Optional[str] = None


class DouyinTargetCreate(BaseModel):
    account_id: str
    item_id: str
    title: str
    poll_interval: int = 300


class DouyinTargetOut(TimestampedModel):
    tenant_id: str
    account_id: str
    item_id: str
    title: str
    status: str
    poll_interval: int
    last_polled_at: Optional[datetime] = None


class DouyinCommentOut(TimestampedModel):
    tenant_id: str
    target_id: str
    account_id: str
    comment_id: str
    parent_comment_id: Optional[str] = None
    user_open_id: Optional[str] = None
    user_nickname: str
    user_avatar_url: Optional[str] = None
    content: str
    posted_at: datetime
    digg_count: int
    reply_count: int
    is_top_level: bool
    is_handled: bool
    is_replied: bool
    raw_payload: dict


class DouyinCommentHandledUpdate(BaseModel):
    comment_ids: list[str]
    is_handled: bool


class DouyinReplyActionOut(TimestampedModel):
    tenant_id: str
    account_id: str
    comment_id: str
    operator_id: Optional[str] = None
    content: str
    response_payload: Optional[dict] = None
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


class DouyinReplySendRequest(BaseModel):
    comment_id: str
    account_id: str
    content: str


class DouyinPersonalCookieImport(BaseModel):
    cookie: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    external_user_id: Optional[str] = None


class DouyinPersonalLoginStartOut(BaseModel):
    session_id: str
    helper_session_id: str
    status: str
    login_url: Optional[str] = None
    qr_image_base64: Optional[str] = None
    expires_at: datetime


class DouyinPersonalLoginStatusOut(BaseModel):
    session_id: str
    helper_session_id: str
    status: str
    account_id: Optional[str] = None
    nickname: Optional[str] = None
    external_user_id: Optional[str] = None
    detail: Optional[str] = None


class DouyinPersonalAccountOut(TimestampedModel):
    tenant_id: str
    integration_type: str = "personal"
    nickname: str
    avatar_url: Optional[str] = None
    external_user_id: str
    status: str
    last_validated_at: Optional[datetime] = None
    last_error: Optional[str] = None


class DouyinPersonalTargetCreate(BaseModel):
    account_id: str
    aweme_id: Optional[str] = None
    video_url: Optional[str] = None
    title: Optional[str] = None
    poll_interval: int = 300


class DouyinPersonalTargetOut(TimestampedModel):
    tenant_id: str
    integration_type: str = "personal"
    account_id: str
    aweme_id: str
    video_url: Optional[str] = None
    title: str
    status: str
    poll_interval: int
    last_polled_at: Optional[datetime] = None


class DouyinPersonalCommentOut(TimestampedModel):
    tenant_id: str
    integration_type: str = "personal"
    target_id: str
    account_id: str
    comment_id: str
    parent_comment_id: Optional[str] = None
    user_external_id: Optional[str] = None
    user_nickname: str
    user_avatar_url: Optional[str] = None
    content: str
    posted_at: datetime
    digg_count: int
    reply_count: int
    is_top_level: bool
    is_handled: bool
    is_replied: bool
    raw_payload: dict


class DouyinPersonalCommentHandledUpdate(BaseModel):
    comment_ids: list[str]
    is_handled: bool


class DouyinPersonalReplyActionOut(TimestampedModel):
    tenant_id: str
    integration_type: str = "personal"
    account_id: str
    comment_id: str
    operator_id: Optional[str] = None
    content: str
    response_payload: Optional[dict] = None
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


class DouyinPersonalReplySendRequest(BaseModel):
    comment_id: str
    account_id: str
    content: str
