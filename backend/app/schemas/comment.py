from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel, TimestampedModel
from app.schemas.reply import ReplyActionOut, ReplyDraftOut


class CommentOut(ORMModel):
    id: str
    tenant_id: str
    target_id: str
    account_id: str
    rpid: int
    root_rpid: Optional[int] = None
    parent_rpid: Optional[int] = None
    oid: int
    member_mid: Optional[int] = None
    member_name: str
    message: str
    posted_at: datetime
    like_count: int
    is_top_level: bool
    is_handled: bool
    is_replied: bool
    raw_payload: dict


class CommentHandledUpdate(BaseModel):
    comment_ids: list[str]
    is_handled: bool


class CommentEventOut(TimestampedModel):
    event_type: str
    payload: dict


class CommentDetailOut(CommentOut):
    events: list[CommentEventOut]
    reply_drafts: list[ReplyDraftOut]
    reply_actions: list[ReplyActionOut]
