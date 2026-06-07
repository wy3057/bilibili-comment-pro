from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, OWNER_OR_ADMIN, TenantContext
from app.db.session import get_db
from app.schemas.ai_reply import AIReplyModeUpdate, AIReplyStatusOut
from app.schemas.system import AuditLogOut, SystemMetricsOut, TaskRunOut
from app.services import ai_reply as ai_reply_service
from app.services.audit import log_audit
from app.services import system as system_service

router = APIRouter()


@router.get("/jobs", response_model=list[TaskRunOut])
def jobs(
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> list[TaskRunOut]:
    return system_service.list_task_runs(db, ctx.tenant.id)


@router.get("/metrics", response_model=SystemMetricsOut)
def metrics(
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> SystemMetricsOut:
    return system_service.get_metrics_summary(db, ctx.tenant.id)


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    return system_service.list_audit_logs(db, ctx.tenant.id)


@router.get("/ai-reply", response_model=AIReplyStatusOut)
def ai_reply_status(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
) -> AIReplyStatusOut:
    return AIReplyStatusOut(**ai_reply_service.get_ai_reply_status(db, ctx.tenant.id))


@router.patch("/ai-reply/mode", response_model=AIReplyStatusOut)
def update_ai_reply_mode(
    payload: AIReplyModeUpdate,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> AIReplyStatusOut:
    mode = ai_reply_service.update_tenant_ai_reply_mode(db, ctx.tenant.id, payload.mode)
    log_audit(
        db,
        "ai.reply.mode.update",
        "tenant_ai_setting",
        tenant_id=ctx.tenant.id,
        user=ctx.user,
        payload={"mode": mode},
    )
    db.commit()
    return AIReplyStatusOut(**ai_reply_service.get_ai_reply_status(db, ctx.tenant.id))
