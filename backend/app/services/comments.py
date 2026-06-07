from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.entities import Comment, CommentEvent, ReplyAction, ReplyDraft, User
from app.services.audit import log_audit


def list_comments(
    db: Session,
    tenant_id: str,
    target_id: Optional[str] = None,
    is_handled: Optional[bool] = None,
) -> List[Comment]:
    stmt: Select = select(Comment).where(Comment.tenant_id == tenant_id)
    if target_id:
        stmt = stmt.where(Comment.target_id == target_id)
    if is_handled is not None:
        stmt = stmt.where(Comment.is_handled.is_(is_handled))
    stmt = stmt.order_by(Comment.posted_at.desc())
    return list(db.scalars(stmt).all())


def mark_comments_handled(
    db: Session,
    tenant_id: str,
    comment_ids: List[str],
    is_handled: bool,
    user: Optional[User] = None,
) -> int:
    rows = db.scalars(select(Comment).where(Comment.tenant_id == tenant_id, Comment.id.in_(comment_ids))).all()
    changed_ids: List[str] = []
    for row in rows:
        if row.is_handled == is_handled:
            continue
        row.is_handled = is_handled
        db.add(row)
        changed_ids.append(row.id)
    if changed_ids:
        log_audit(
            db,
            "comment.handle.update",
            "comment",
            tenant_id=tenant_id,
            user=user,
            payload={"comment_ids": changed_ids, "is_handled": is_handled},
        )
    db.commit()
    return len(changed_ids)


def get_comment(db: Session, tenant_id: str, comment_id: str) -> Optional[Comment]:
    return db.scalar(select(Comment).where(Comment.tenant_id == tenant_id, Comment.id == comment_id))


def get_comment_detail(db: Session, tenant_id: str, comment_id: str) -> Optional[Dict[str, object]]:
    comment = get_comment(db, tenant_id, comment_id)
    if comment is None:
        return None
    events = list(
        db.scalars(
            select(CommentEvent).where(CommentEvent.comment_id == comment_id).order_by(CommentEvent.created_at.desc())
        ).all()
    )
    reply_actions = list(
        db.scalars(
            select(ReplyAction)
            .where(ReplyAction.tenant_id == tenant_id, ReplyAction.comment_id == comment_id)
            .order_by(ReplyAction.created_at.desc())
        ).all()
    )
    reply_drafts = list(
        db.scalars(
            select(ReplyDraft)
            .where(ReplyDraft.tenant_id == tenant_id, ReplyDraft.comment_id == comment_id)
            .order_by(ReplyDraft.created_at.desc())
        ).all()
    )
    return {"comment": comment, "events": events, "reply_drafts": reply_drafts, "reply_actions": reply_actions}
