from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AIReplyGenerateRequest(BaseModel):
    platform: str
    integration_type: Optional[str] = None
    comment_id: str
    account_id: str
    extra_instruction: Optional[str] = None


class AIReplyGenerateResponse(BaseModel):
    content: str
    mode: str
    sent: bool


class AIReplyStatusOut(BaseModel):
    enabled: bool
    provider: str
    model: str
    base_url: str
    api_mode: str
    mode: str


class AIReplyModeUpdate(BaseModel):
    mode: str
