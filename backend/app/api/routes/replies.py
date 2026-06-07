from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.schemas.reply import ReplyActionOut, ReplySendRequest
from app.services import replies as reply_service

router = APIRouter()


@router.get("", response_model=list[ReplyActionOut])
def list_reply_actions(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[ReplyActionOut]:
    return reply_service.list_reply_actions(db, ctx.tenant.id)


@router.post("/send", response_model=ReplyActionOut)
async def send_reply(
    payload: ReplySendRequest,
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> ReplyActionOut:
    return await reply_service.send_reply(
        db,
        tenant_id=ctx.tenant.id,
        account_id=payload.account_id,
        comment_id=payload.comment_id,
        content=payload.content,
        draft_id=payload.draft_id,
        user=ctx.user,
    )
