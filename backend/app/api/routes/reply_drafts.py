from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.schemas.reply import ReplyDraftCreate, ReplyDraftOut
from app.services import replies as reply_service

router = APIRouter()


@router.post("", response_model=ReplyDraftOut)
def create_draft(
    payload: ReplyDraftCreate,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> ReplyDraftOut:
    return reply_service.create_draft(db, ctx.tenant.id, payload.comment_id, payload.content, ctx.user)

