from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AuditLog,
    BilibiliAccount,
    DouyinAccount,
    DouyinPersonalAccount,
    DouyinPersonalTarget,
    DouyinTarget,
    MonitorTarget,
    TaskRun,
)
from app.schemas.system import SystemMetricsOut


def list_audit_logs(db: Session, tenant_id: str) -> List[AuditLog]:
    stmt = select(AuditLog).where((AuditLog.tenant_id == tenant_id) | (AuditLog.tenant_id.is_(None))).order_by(
        AuditLog.created_at.desc()
    )
    return list(db.scalars(stmt).all())


def list_task_runs(db: Session, tenant_id: str) -> List[TaskRun]:
    stmt = select(TaskRun).where((TaskRun.tenant_id == tenant_id) | (TaskRun.tenant_id.is_(None))).order_by(
        TaskRun.created_at.desc()
    )
    return list(db.scalars(stmt).all())


def get_metrics_summary(db: Session, tenant_id: str) -> SystemMetricsOut:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    queue_backlog = db.scalar(select(func.count(TaskRun.id)).where(TaskRun.tenant_id == tenant_id, TaskRun.status == "running")) or 0
    failed_tasks_last_24h = db.scalar(
        select(func.count(TaskRun.id)).where(
            TaskRun.tenant_id == tenant_id,
            TaskRun.status == "failed",
            TaskRun.finished_at.is_not(None),
            TaskRun.finished_at >= since,
        )
    ) or 0
    bilibili_expired_accounts = db.scalar(
        select(func.count(BilibiliAccount.id)).where(BilibiliAccount.tenant_id == tenant_id, BilibiliAccount.status == "expired")
    ) or 0
    douyin_expired_accounts = db.scalar(
        select(func.count(DouyinAccount.id)).where(DouyinAccount.tenant_id == tenant_id, DouyinAccount.status == "expired")
    ) or 0
    douyin_personal_expired_accounts = db.scalar(
        select(func.count(DouyinPersonalAccount.id)).where(
            DouyinPersonalAccount.tenant_id == tenant_id,
            DouyinPersonalAccount.status == "expired",
        )
    ) or 0
    bilibili_active_targets = db.scalar(
        select(func.count(MonitorTarget.id)).where(MonitorTarget.tenant_id == tenant_id, MonitorTarget.status == "active")
    ) or 0
    douyin_active_targets = db.scalar(
        select(func.count(DouyinTarget.id)).where(DouyinTarget.tenant_id == tenant_id, DouyinTarget.status == "active")
    ) or 0
    douyin_personal_active_targets = db.scalar(
        select(func.count(DouyinPersonalTarget.id)).where(
            DouyinPersonalTarget.tenant_id == tenant_id,
            DouyinPersonalTarget.status == "active",
        )
    ) or 0
    risk_accounts = db.scalar(
        select(func.count(BilibiliAccount.id)).where(BilibiliAccount.tenant_id == tenant_id, BilibiliAccount.risk_status != "normal")
    ) or 0
    return SystemMetricsOut(
        queue_backlog=int(queue_backlog),
        failed_tasks_last_24h=int(failed_tasks_last_24h),
        login_expired_accounts=int(
            bilibili_expired_accounts + douyin_expired_accounts + douyin_personal_expired_accounts
        ),
        active_targets=int(bilibili_active_targets + douyin_active_targets + douyin_personal_active_targets),
        risk_accounts=int(risk_accounts),
    )
