from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class TargetCreate(BaseModel):
    account_id: str
    oid: int
    bvid: str
    title: str
    owner_mid: Optional[int] = None
    poll_interval: int = 300


class TargetUpdate(BaseModel):
    status: Optional[str] = None
    poll_interval: Optional[int] = None
    title: Optional[str] = None


class TargetImportRequest(BaseModel):
    only_missing: bool = True
    selected_bvids: Optional[List[str]] = None
    poll_interval: int = 300


class TargetOut(ORMModel):
    id: str
    tenant_id: str
    account_id: str
    oid: int
    bvid: str
    title: str
    owner_mid: Optional[int] = None
    status: str
    poll_interval: int
    last_polled_at: Optional[datetime] = None


class ImportedTargetCandidate(BaseModel):
    oid: int
    bvid: str
    title: str
    owner_mid: Optional[int] = None
    already_monitored: bool = False
