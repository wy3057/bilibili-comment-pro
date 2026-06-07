from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import OWNER_OR_ADMIN, TenantContext
from app.db.session import get_db
from app.schemas.system import AuditLogOut
from app.services import system as system_service

router = APIRouter()


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    return system_service.list_audit_logs(db, ctx.tenant.id)

