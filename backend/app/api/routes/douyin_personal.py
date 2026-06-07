from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.models.entities import DouyinPersonalAccount, DouyinPersonalTarget
from app.schemas.douyin import (
    DouyinPersonalAccountOut,
    DouyinPersonalCommentHandledUpdate,
    DouyinPersonalCommentOut,
    DouyinPersonalCookieImport,
    DouyinPersonalLoginStartOut,
    DouyinPersonalLoginStatusOut,
    DouyinPersonalReplyActionOut,
    DouyinPersonalReplySendRequest,
    DouyinPersonalTargetCreate,
    DouyinPersonalTargetOut,
)
from app.services import douyin_personal as douyin_personal_service

router = APIRouter()


@router.post("/login/start", response_model=DouyinPersonalLoginStartOut)
async def start_login(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinPersonalLoginStartOut:
    session = await douyin_personal_service.start_login_session(db, ctx.tenant.id, ctx.user)
    return DouyinPersonalLoginStartOut(
        session_id=session.id,
        helper_session_id=session.helper_session_id,
        status=session.status,
        login_url=session.login_url,
        qr_image_base64=session.qr_image_base64,
        expires_at=session.expires_at,
    )


@router.get("/login/{session_id}", response_model=DouyinPersonalLoginStatusOut)
async def login_status(
    session_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinPersonalLoginStatusOut:
    payload = await douyin_personal_service.get_login_session_status(db, ctx.tenant.id, session_id, ctx.user)
    return DouyinPersonalLoginStatusOut(**payload)


@router.post("/accounts/import-cookie", response_model=DouyinPersonalAccountOut)
async def import_cookie(
    payload: DouyinPersonalCookieImport,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinPersonalAccountOut:
    return await douyin_personal_service.import_cookie_account(db, ctx.tenant.id, payload, ctx.user)


@router.get("/accounts", response_model=list[DouyinPersonalAccountOut])
def list_accounts(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinPersonalAccountOut]:
    return douyin_personal_service.list_accounts(db, ctx.tenant.id)


@router.post("/accounts/{account_id}/refresh-runtime", response_model=DouyinPersonalAccountOut)
async def refresh_runtime(
    account_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinPersonalAccountOut:
    account = db.get(DouyinPersonalAccount, account_id)
    if account is None or account.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Douyin personal account not found")
    return await douyin_personal_service.refresh_runtime(db, account, ctx.user)


@router.get("/targets", response_model=list[DouyinPersonalTargetOut])
def list_targets(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinPersonalTargetOut]:
    return douyin_personal_service.list_targets(db, ctx.tenant.id)


@router.post("/targets", response_model=DouyinPersonalTargetOut)
async def create_target(
    payload: DouyinPersonalTargetCreate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinPersonalTargetOut:
    return await douyin_personal_service.create_target(db, ctx.tenant.id, payload, ctx.user)


@router.post("/targets/{target_id}/poll")
async def poll_target(
    target_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(DouyinPersonalTarget, target_id)
    if target is None or target.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Douyin personal target not found")
    return await douyin_personal_service.gateway.poll_target_comments(db, target)


@router.get("/comments", response_model=list[DouyinPersonalCommentOut])
def list_comments(
    target_id: Optional[str] = Query(default=None),
    is_handled: Optional[bool] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinPersonalCommentOut]:
    return douyin_personal_service.list_comments(db, ctx.tenant.id, target_id=target_id, is_handled=is_handled)


@router.patch("/comments/handled")
def mark_comments_handled(
    payload: DouyinPersonalCommentHandledUpdate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    updated = douyin_personal_service.mark_comments_handled(
        db,
        ctx.tenant.id,
        payload.comment_ids,
        payload.is_handled,
        ctx.user,
    )
    return {"updated": updated}


@router.get("/reply-actions", response_model=list[DouyinPersonalReplyActionOut])
def list_reply_actions(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinPersonalReplyActionOut]:
    return douyin_personal_service.list_reply_actions(db, ctx.tenant.id)


@router.post("/reply-actions/send", response_model=DouyinPersonalReplyActionOut)
async def send_reply(
    payload: DouyinPersonalReplySendRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinPersonalReplyActionOut:
    return await douyin_personal_service.gateway.reply_to_comment(
        db,
        tenant_id=ctx.tenant.id,
        account_id=payload.account_id,
        comment_id=payload.comment_id,
        content=payload.content,
        user=ctx.user,
    )
