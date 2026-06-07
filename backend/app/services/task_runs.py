from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.metrics import TASK_RUN_DURATION_SECONDS, TASK_RUNS_TOTAL
from app.models.entities import TaskKind, TaskRun, TaskStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def start_task_run(
    db: Session,
    task_name: str,
    task_kind: str,
    tenant_id: Optional[str] = None,
    account_id: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> TaskRun:
    task_run = TaskRun(
        tenant_id=tenant_id,
        account_id=account_id,
        target_id=target_id,
        task_name=task_name,
        task_kind=task_kind,
        status=TaskStatus.running.value,
        started_at=_utcnow(),
        detail=detail or {},
    )
    db.add(task_run)
    db.flush()
    return task_run


def finish_task_run(
    db: Session,
    task_run: TaskRun,
    status: str,
    detail: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> TaskRun:
    finished_at = _utcnow()
    started_at = _normalize_datetime(task_run.started_at)
    task_run.finished_at = finished_at
    task_run.status = status
    task_run.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    task_run.detail = detail or task_run.detail
    task_run.error_message = error_message
    db.add(task_run)
    db.flush()
    TASK_RUNS_TOTAL.labels(task_run.task_name, status).inc()
    TASK_RUN_DURATION_SECONDS.labels(task_run.task_name, status).observe(
        task_run.duration_ms / 1000 if task_run.duration_ms is not None else 0
    )
    return task_run
