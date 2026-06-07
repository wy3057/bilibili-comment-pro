from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel, TimestampedModel


class AuditLogOut(TimestampedModel):
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    payload: dict
    ip_address: Optional[str] = None


class TaskRunOut(ORMModel):
    id: str
    tenant_id: Optional[str] = None
    account_id: Optional[str] = None
    target_id: Optional[str] = None
    task_name: str
    task_kind: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    detail: dict
    error_message: Optional[str] = None


class SystemMetricsOut(BaseModel):
    queue_backlog: int
    failed_tasks_last_24h: int
    login_expired_accounts: int
    active_targets: int
    risk_accounts: int
