from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.models.entities import BilibiliAccount
from app.schemas.bilibili import BilibiliAccountOut, BilibiliCredentialImport, QrCodeSessionOut, QrCodeStatusOut
from app.services.bilibili_gateway import gateway

router = APIRouter()


@router.get("/accounts", response_model=list[BilibiliAccountOut])
def list_accounts(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[BilibiliAccountOut]:
    rows = db.scalars(
        select(BilibiliAccount).where(BilibiliAccount.tenant_id == ctx.tenant.id).order_by(BilibiliAccount.created_at.desc())
    ).all()
    return list(rows)


@router.post("/accounts/qrcode/start", response_model=QrCodeSessionOut)
async def start_qrcode(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
) -> QrCodeSessionOut:
    return await gateway.start_qr_login(ctx.tenant.id, ctx.user.id)


@router.get("/accounts/qrcode/{session_id}", response_model=QrCodeStatusOut)
async def check_qrcode(
    session_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> QrCodeStatusOut:
    return await gateway.check_qr_login(db, session_id, ctx.user.id)


@router.post("/accounts/import-credentials", response_model=BilibiliAccountOut)
async def import_credentials(
    payload: BilibiliCredentialImport,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> BilibiliAccountOut:
    return await gateway.import_credentials(db, ctx.tenant.id, ctx.user.id, payload)


@router.post("/accounts/{account_id}/refresh", response_model=BilibiliAccountOut)
async def refresh_account(
    account_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> BilibiliAccountOut:
    account = db.get(BilibiliAccount, account_id)
    if not account or account.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Account not found")
    return await gateway.refresh_account(db, account)

