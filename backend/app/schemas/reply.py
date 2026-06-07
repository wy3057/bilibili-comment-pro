from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel, TimestampedModel


class ReplyDraftCreate(BaseModel):
    comment_id: str
    content: str


class ReplyDraftOut(TimestampedModel):
    tenant_id: str
    comment_id: str
    operator_id: Optional[str] = None
    content: str
    status: str


class ReplySendRequest(BaseModel):
    comment_id: str
    account_id: str
    content: Optional[str] = None
    draft_id: Optional[str] = None


class ReplyActionOut(TimestampedModel):
    tenant_id: str
    account_id: str
    comment_id: str
    draft_id: Optional[str] = None
    operator_id: Optional[str] = None
    request_payload: dict
    response_payload: Optional[dict] = None
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
