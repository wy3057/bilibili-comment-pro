from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import BilibiliAccount, Comment, ReplyAction, ReplyActionStatus, ReplyDraft, User
from app.services.audit import log_audit
from app.services.bilibili_gateway import gateway


def create_draft(db: Session, tenant_id: str, comment_id: str, content: str, user: User) -> ReplyDraft:
    comment_row = db.scalar(select(Comment).where(Comment.tenant_id == tenant_id, Comment.id == comment_id))
    if comment_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    draft = ReplyDraft(
        tenant_id=tenant_id,
        comment_id=comment_id,
        operator_id=user.id,
        content=content,
        status="draft",
    )
    db.add(draft)
    db.flush()
    log_audit(
        db,
        "reply.draft.create",
        "reply_draft",
        entity_id=draft.id,
        tenant_id=tenant_id,
        user=user,
        payload={"comment_id": comment_id, "content_length": len(content)},
    )
    db.commit()
    db.refresh(draft)
    return draft


def list_reply_actions(db: Session, tenant_id: str) -> List[ReplyAction]:
    return list(
        db.scalars(select(ReplyAction).where(ReplyAction.tenant_id == tenant_id).order_by(ReplyAction.created_at.desc())).all()
    )


async def send_reply(
    db: Session,
    tenant_id: str,
    account_id: str,
    comment_id: str,
    content: Optional[str],
    draft_id: Optional[str],
    user: User,
) -> ReplyAction:
    comment_row = db.scalar(select(Comment).where(Comment.tenant_id == tenant_id, Comment.id == comment_id))
    if comment_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    account = db.scalar(select(BilibiliAccount).where(BilibiliAccount.tenant_id == tenant_id, BilibiliAccount.id == account_id))
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    draft = None
    if draft_id:
        draft = db.scalar(select(ReplyDraft).where(ReplyDraft.tenant_id == tenant_id, ReplyDraft.id == draft_id))
        if draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    final_content = content or (draft.content if draft else None)
    if not final_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reply content required")

    action = ReplyAction(
        tenant_id=tenant_id,
        account_id=account.id,
        comment_id=comment_row.id,
        draft_id=draft.id if draft else None,
        operator_id=user.id,
        request_payload={},
        status=ReplyActionStatus.pending.value,
    )
    db.add(action)
    db.flush()
    log_audit(
        db,
        "reply.send.requested",
        "reply_action",
        entity_id=action.id,
        tenant_id=tenant_id,
        user=user,
        payload={"comment_id": comment_id, "account_id": account_id},
    )
    db.commit()
    db.refresh(action)
    result = await gateway.send_reply(db, action, account, comment_row, final_content)
    log_audit(
        db,
        "reply.send.completed" if result.status == ReplyActionStatus.sent.value else "reply.send.failed",
        "reply_action",
        entity_id=result.id,
        tenant_id=tenant_id,
        user=user,
        payload={
            "comment_id": comment_id,
            "account_id": account_id,
            "status": result.status,
            "error_message": result.error_message,
        },
    )
    if draft:
        draft.status = "sent" if result.status == "sent" else draft.status
        db.add(draft)
    db.commit()
    return result
