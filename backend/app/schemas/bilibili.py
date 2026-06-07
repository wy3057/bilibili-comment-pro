from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class BilibiliCredentialImport(BaseModel):
    sessdata: str
    bili_jct: str
    buvid3: Optional[str] = None
    buvid4: Optional[str] = None
    dedeuserid: Optional[str] = None
    ac_time_value: Optional[str] = None


class QrCodeSessionOut(BaseModel):
    session_id: str
    login_url: str
    qr_terminal: str
    qr_image_base64: str
    status: str


class QrCodeStatusOut(BaseModel):
    session_id: str
    status: str
    account_id: Optional[str] = None
    username: Optional[str] = None
    uid: Optional[int] = None
    detail: Optional[str] = None


class BilibiliAccountOut(ORMModel):
    id: str
    tenant_id: str
    uid: int
    username: str
    avatar_url: Optional[str] = None
    status: str
    risk_status: str
    last_validated_at: Optional[datetime] = None
    last_refreshed_at: Optional[datetime] = None
    last_error: Optional[str] = None
