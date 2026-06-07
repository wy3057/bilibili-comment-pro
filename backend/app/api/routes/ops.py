from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.schemas.ai_reply import AIReplyGenerateRequest, AIReplyGenerateResponse
from app.schemas.ops import (
    PlatformAccountOut,
    PlatformCommentDetailOut,
    PlatformCommentHandledUpdate,
    PlatformCommentOut,
    PlatformReplyActionOut,
    PlatformReplySendRequest,
    PlatformTargetOut,
)
from app.services import ai_reply as ai_reply_service
from app.services import ops as ops_service

router = APIRouter()


@router.get("/accounts", response_model=list[PlatformAccountOut])
def list_accounts(
    platform: Optional[str] = Query(default=None),
    integration_type: Optional[str] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[PlatformAccountOut]:
    return ops_service.list_accounts(db, ctx.tenant.id, platform=platform, integration_type=integration_type)


@router.get("/targets", response_model=list[PlatformTargetOut])
def list_targets(
    platform: Optional[str] = Query(default=None),
    integration_type: Optional[str] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[PlatformTargetOut]:
    return ops_service.list_targets(db, ctx.tenant.id, platform=platform, integration_type=integration_type)


@router.get("/comments", response_model=list[PlatformCommentOut])
def list_comments(
    platform: Optional[str] = Query(default=None),
    integration_type: Optional[str] = Query(default=None),
    target_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    is_handled: Optional[bool] = Query(default=None),
    is_replied: Optional[bool] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[PlatformCommentOut]:
    return ops_service.list_comments(
        db,
        ctx.tenant.id,
        platform=platform,
        integration_type=integration_type,
        target_id=target_id,
        account_id=account_id,
        is_handled=is_handled,
        is_replied=is_replied,
        keyword=keyword,
    )


@router.get("/comments/{platform}/{comment_id}", response_model=PlatformCommentDetailOut)
def get_comment_detail(
    platform: str,
    comment_id: str,
    integration_type: Optional[str] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> PlatformCommentDetailOut:
    return ops_service.get_comment_detail(
        db,
        ctx.tenant.id,
        platform,
        comment_id,
        integration_type=integration_type,
    )


@router.patch("/comments/handled")
def mark_comments_handled(
    payload: PlatformCommentHandledUpdate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    updated = ops_service.mark_comments_handled(
        db,
        ctx.tenant.id,
        [item.model_dump() for item in payload.items],
        payload.is_handled,
        ctx.user,
    )
    return {"updated": updated}


@router.post("/replies/generate", response_model=AIReplyGenerateResponse)
async def generate_reply(
    payload: AIReplyGenerateRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> AIReplyGenerateResponse:
    content, sent = await ops_service.generate_reply_suggestion(
        db,
        ctx.tenant.id,
        platform=payload.platform,
        comment_id=payload.comment_id,
        account_id=payload.account_id,
        integration_type=payload.integration_type,
        extra_instruction=payload.extra_instruction,
        user=ctx.user,
    )
    return AIReplyGenerateResponse(
        content=content,
        mode=ai_reply_service.get_tenant_ai_reply_mode(db, ctx.tenant.id),
        sent=sent,
    )


@router.post("/replies/send", response_model=PlatformReplyActionOut)
async def send_reply(
    payload: PlatformReplySendRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> PlatformReplyActionOut:
    return await ops_service.send_reply(db, ctx.tenant.id, payload, ctx.user)


@router.get("/reply-actions", response_model=list[PlatformReplyActionOut])
def list_reply_actions(
    platform: Optional[str] = Query(default=None),
    integration_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[PlatformReplyActionOut]:
    return ops_service.list_reply_actions(
        db,
        ctx.tenant.id,
        platform=platform,
        integration_type=integration_type,
        status=status,
        account_id=account_id,
    )
