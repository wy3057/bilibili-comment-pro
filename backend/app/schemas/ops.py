from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.schemas.common import TimestampedModel

Platform = Literal["bilibili", "douyin"]
IntegrationType = Literal["enterprise", "personal"]


class PlatformAccountOut(TimestampedModel):
    platform: Platform
    integration_type: Optional[IntegrationType] = None
    tenant_id: str
    display_name: str
    external_id: str
    avatar_url: Optional[str] = None
    status: str
    risk_status: Optional[str] = None
    last_validated_at: Optional[datetime] = None
    last_refreshed_at: Optional[datetime] = None
    access_token_expires_at: Optional[datetime] = None
    last_error: Optional[str] = None


class PlatformTargetOut(TimestampedModel):
    platform: Platform
    integration_type: Optional[IntegrationType] = None
    tenant_id: str
    account_id: str
    title: str
    external_id: str
    status: str
    poll_interval: int
    last_polled_at: Optional[datetime] = None


class PlatformReplyDraftOut(TimestampedModel):
    id: str
    content: str
    status: str


class PlatformReplyActionOut(TimestampedModel):
    platform: Platform
    integration_type: Optional[IntegrationType] = None
    tenant_id: str
    account_id: str
    comment_id: str
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    content: Optional[str] = None


class PlatformCommentOut(TimestampedModel):
    platform: Platform
    integration_type: Optional[IntegrationType] = None
    tenant_id: str
    target_id: str
    account_id: str
    external_id: str
    parent_external_id: Optional[str] = None
    author_name: str
    author_avatar_url: Optional[str] = None
    content: str
    posted_at: datetime
    like_count: int
    reply_count: int
    is_top_level: bool
    is_handled: bool
    is_replied: bool
    raw_payload: dict


class PlatformCommentEventOut(TimestampedModel):
    event_type: str
    payload: dict


class PlatformCommentDetailOut(PlatformCommentOut):
    events: list[PlatformCommentEventOut]
    reply_drafts: list[PlatformReplyDraftOut]
    reply_actions: list[PlatformReplyActionOut]


class PlatformCommentRef(BaseModel):
    platform: Platform
    integration_type: Optional[IntegrationType] = None
    id: str


class PlatformCommentHandledUpdate(BaseModel):
    items: list[PlatformCommentRef]
    is_handled: bool


class PlatformReplySendRequest(BaseModel):
    platform: Platform
    integration_type: Optional[IntegrationType] = None
    comment_id: str
    account_id: str
    content: Optional[str] = None
    draft_id: Optional[str] = None
