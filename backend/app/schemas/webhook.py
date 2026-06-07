from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class WebhookConfigCreate(BaseModel):
    name: str
    provider: str
    webhook_url: str
    is_enabled: bool = True


class WebhookConfigUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    webhook_url: Optional[str] = None
    is_enabled: Optional[bool] = None


class WebhookConfigOut(ORMModel):
    id: str
    tenant_id: str
    name: str
    provider: str
    is_enabled: bool


class WebhookTestResult(BaseModel):
    ok: bool
    detail: str

