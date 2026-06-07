from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import DouyinAccount, DouyinOAuthSession, DouyinTarget, User
from app.schemas.douyin import (
    DouyinAccountImport,
    DouyinAccountOut,
    DouyinAppCreate,
    DouyinAppOut,
    DouyinOAuthExchangeCodeRequest,
    DouyinOAuthStartOut,
    DouyinOAuthStartRequest,
    DouyinCommentHandledUpdate,
    DouyinCommentOut,
    DouyinReplyActionOut,
    DouyinReplySendRequest,
    DouyinTargetCreate,
    DouyinTargetOut,
)
from app.services import douyin as douyin_service

router = APIRouter()


def _append_oauth_status(path: str, oauth_status: str) -> str:
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}oauth={oauth_status}"


@router.get("/apps", response_model=list[DouyinAppOut])
def list_apps(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinAppOut]:
    return douyin_service.list_apps(db, ctx.tenant.id)


@router.post("/apps", response_model=DouyinAppOut)
def create_app(
    payload: DouyinAppCreate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinAppOut:
    return douyin_service.create_app(db, ctx.tenant.id, payload, ctx.user)


@router.get("/accounts", response_model=list[DouyinAccountOut])
def list_accounts(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinAccountOut]:
    return douyin_service.list_accounts(db, ctx.tenant.id)


@router.post("/accounts/import-authorization", response_model=DouyinAccountOut)
async def import_authorization(
    payload: DouyinAccountImport,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinAccountOut:
    return await douyin_service.import_account(db, ctx.tenant.id, payload, ctx.user)


@router.post("/oauth/start", response_model=DouyinOAuthStartOut)
def start_oauth(
    payload: DouyinOAuthStartRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinOAuthStartOut:
    session, auth_url = douyin_service.start_oauth_session(
        db,
        ctx.tenant.id,
        ctx.user,
        payload.app_id,
        payload.redirect_path,
    )
    return DouyinOAuthStartOut(
        session_id=session.id,
        state=session.state,
        auth_url=auth_url,
        expires_at=session.expires_at,
    )


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    session = db.scalar(select(DouyinOAuthSession).where(DouyinOAuthSession.state == state))
    if session is None:
        return RedirectResponse(f"{settings.public_web_base_url.rstrip('/')}/ops?tab=accounts&platform=douyin&oauth=missing")
    now = datetime.now(timezone.utc)
    if session.consumed_at is not None or session.expires_at < now:
        session.status = "expired"
        db.add(session)
        db.commit()
        return RedirectResponse(f"{settings.public_web_base_url.rstrip('/')}/ops?tab=accounts&platform=douyin&oauth=expired")
    user = db.get(User, session.user_id)
    if user is None:
        return RedirectResponse(f"{settings.public_web_base_url.rstrip('/')}/ops?tab=accounts&platform=douyin&oauth=user_missing")
    try:
        await douyin_service.exchange_code_for_account(db, session.tenant_id, user, session.app_id, code)
        session.consumed_at = now
        session.status = "done"
        db.add(session)
        db.commit()
        return RedirectResponse(
            f"{settings.public_web_base_url.rstrip('/')}{_append_oauth_status(session.redirect_path, 'success')}"
        )
    except Exception:
        session.status = "failed"
        db.add(session)
        db.commit()
        return RedirectResponse(
            f"{settings.public_web_base_url.rstrip('/')}{_append_oauth_status(session.redirect_path, 'failed')}"
        )


@router.post("/oauth/exchange-code", response_model=DouyinAccountOut)
async def exchange_code(
    payload: DouyinOAuthExchangeCodeRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinAccountOut:
    return await douyin_service.exchange_code_for_account(db, ctx.tenant.id, ctx.user, payload.app_id, payload.code)


@router.post("/accounts/{account_id}/refresh", response_model=DouyinAccountOut)
async def refresh_account(
    account_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinAccountOut:
    account = db.get(DouyinAccount, account_id)
    if account is None or account.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Douyin account not found")
    return await douyin_service.gateway.refresh_account(db, account)


@router.get("/targets", response_model=list[DouyinTargetOut])
def list_targets(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinTargetOut]:
    return douyin_service.list_targets(db, ctx.tenant.id)


@router.post("/targets", response_model=DouyinTargetOut)
def create_target(
    payload: DouyinTargetCreate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinTargetOut:
    return douyin_service.create_target(db, ctx.tenant.id, payload, ctx.user)


@router.post("/targets/{target_id}/poll")
async def poll_target(
    target_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(DouyinTarget, target_id)
    if target is None or target.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Douyin target not found")
    return await douyin_service.gateway.poll_target_comments(db, target)


@router.get("/comments", response_model=list[DouyinCommentOut])
def list_comments(
    target_id: Optional[str] = Query(default=None),
    is_handled: Optional[bool] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinCommentOut]:
    return douyin_service.list_comments(db, ctx.tenant.id, target_id=target_id, is_handled=is_handled)


@router.patch("/comments/handled")
def mark_comments_handled(
    payload: DouyinCommentHandledUpdate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    updated = douyin_service.mark_comments_handled(
        db,
        ctx.tenant.id,
        payload.comment_ids,
        payload.is_handled,
        ctx.user,
    )
    return {"updated": updated}


@router.get("/reply-actions", response_model=list[DouyinReplyActionOut])
def list_reply_actions(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[DouyinReplyActionOut]:
    return douyin_service.list_reply_actions(db, ctx.tenant.id)


@router.post("/reply-actions/send", response_model=DouyinReplyActionOut)
async def send_reply(
    payload: DouyinReplySendRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> DouyinReplyActionOut:
    return await douyin_service.gateway.reply_to_comment(
        db,
        tenant_id=ctx.tenant.id,
        account_id=payload.account_id,
        comment_id=payload.comment_id,
        content=payload.content,
        user=ctx.user,
    )
