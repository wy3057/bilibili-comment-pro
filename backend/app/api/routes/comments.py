from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.models.entities import MonitorTarget
from app.schemas.comment import CommentDetailOut, CommentEventOut, CommentHandledUpdate, CommentOut
from app.schemas.reply import ReplyActionOut, ReplyDraftOut
from app.services import comments as comment_service
from app.services.bilibili_gateway import gateway

router = APIRouter()


@router.get("", response_model=list[CommentOut])
def list_comments(
    target_id: Optional[str] = Query(default=None),
    is_handled: Optional[bool] = Query(default=None),
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[CommentOut]:
    return comment_service.list_comments(db, ctx.tenant.id, target_id=target_id, is_handled=is_handled)


@router.get("/target/{target_id}", response_model=list[CommentOut])
def get_target_comments(
    target_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[CommentOut]:
    return comment_service.list_comments(db, ctx.tenant.id, target_id=target_id)


@router.patch("/handled")
def mark_handled(
    payload: CommentHandledUpdate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    count = comment_service.mark_comments_handled(
        db,
        ctx.tenant.id,
        payload.comment_ids,
        payload.is_handled,
        ctx.user,
    )
    return {"updated": count}


@router.post("/target/{target_id}/poll")
async def poll_target_comments(
    target_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(MonitorTarget, target_id)
    if target is None or target.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Target not found")
    return await gateway.poll_target_comments(db, target)


@router.get("/{comment_id}", response_model=CommentDetailOut)
def get_comment(
    comment_id: str,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> CommentDetailOut:
    detail = comment_service.get_comment_detail(db, ctx.tenant.id, comment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    row = CommentOut.model_validate(detail["comment"])
    return CommentDetailOut(
        **row.model_dump(),
        events=[CommentEventOut.model_validate(item) for item in detail["events"]],
        reply_drafts=[ReplyDraftOut.model_validate(item) for item in detail["reply_drafts"]],
        reply_actions=[ReplyActionOut.model_validate(item) for item in detail["reply_actions"]],
    )
