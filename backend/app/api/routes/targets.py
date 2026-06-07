from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.models.entities import BilibiliAccount, MonitorTarget
from app.schemas.comment import CommentOut
from app.schemas.target import ImportedTargetCandidate, TargetCreate, TargetImportRequest, TargetOut, TargetUpdate
from app.services import comments as comment_service
from app.services import targets as target_service

router = APIRouter()


@router.get("", response_model=list[TargetOut])
def list_targets(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[TargetOut]:
    return target_service.list_targets(db, ctx.tenant.id)


@router.post("", response_model=TargetOut)
def create_target(
    payload: TargetCreate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> TargetOut:
    return target_service.create_target(db, ctx.tenant.id, payload, ctx.user)


@router.patch("/{target_id}", response_model=TargetOut)
def update_target(
    target_id: str,
    payload: TargetUpdate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> TargetOut:
    target = db.get(MonitorTarget, target_id)
    if target is None or target.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Target not found")
    return target_service.update_target(db, target, payload, ctx.user)


@router.delete("/{target_id}")
def delete_target(
    target_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(MonitorTarget, target_id)
    if target is None or target.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Target not found")
    target_service.delete_target(db, target, ctx.user)
    return {"message": "Deleted"}


@router.post("/import-from-account/{account_id}", response_model=list[TargetOut])
async def import_from_account(
    account_id: str,
    payload: TargetImportRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[TargetOut]:
    account = db.get(BilibiliAccount, account_id)
    if account is None or account.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Account not found")
    return await target_service.import_selected_candidates(
        db,
        ctx.tenant.id,
        account,
        payload.selected_bvids,
        payload.only_missing,
        payload.poll_interval,
        ctx.user,
    )


@router.get("/import-preview/{account_id}", response_model=list[ImportedTargetCandidate])
async def import_preview(
    account_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[ImportedTargetCandidate]:
    account = db.get(BilibiliAccount, account_id)
    if account is None or account.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Account not found")
    return await target_service.preview_import_candidates(db, ctx.tenant.id, account)


@router.get("/{target_id}/comments", response_model=list[CommentOut])
def target_comments(
    target_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[CommentOut]:
    target = db.get(MonitorTarget, target_id)
    if target is None or target.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Target not found")
    return comment_service.list_comments(db, ctx.tenant.id, target_id=target_id)
