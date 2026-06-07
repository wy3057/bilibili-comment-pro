from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.entities import (
    AccountStatus,
    AuditLog,
    BilibiliAccount,
    Comment,
    MonitorTarget,
    ReplyDraft,
    RiskStatus,
    Tenant,
    User,
)
from app.services import replies as reply_service


def _seed_reply_context(db_session):
    tenant = Tenant(name="Tenant Reply", slug="tenant-reply", is_active=True)
    user = User(email="owner-reply@example.com", display_name="Owner", password_hash="hash", is_active=True)
    db_session.add_all([tenant, user])
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(user)

    account = BilibiliAccount(
        tenant_id=tenant.id,
        uid=10001,
        username="reply-account",
        status=AccountStatus.active.value,
        risk_status=RiskStatus.normal.value,
    )
    db_session.add(account)
    db_session.flush()

    target = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=123456,
        bvid="BV1reply111",
        title="Reply Target",
        poll_interval=300,
        status="active",
    )
    db_session.add(target)
    db_session.flush()

    comment = Comment(
        tenant_id=tenant.id,
        target_id=target.id,
        account_id=account.id,
        rpid=9001,
        root_rpid=9001,
        parent_rpid=None,
        oid=123456,
        member_mid=8888,
        member_name="Alice",
        message="Need a reply",
        posted_at=datetime.now(timezone.utc),
        like_count=0,
        is_top_level=True,
        raw_payload={"source": "test"},
    )

    db_session.add(comment)
    db_session.commit()
    db_session.refresh(account)
    db_session.refresh(target)
    db_session.refresh(comment)
    return tenant, user, account, target, comment


def test_create_reply_draft(db_session):
    tenant, user, _account, _target, comment = _seed_reply_context(db_session)

    draft = reply_service.create_draft(
        db_session,
        tenant_id=tenant.id,
        comment_id=comment.id,
        content="This is a draft reply.",
        user=user,
    )

    assert draft.id
    assert draft.tenant_id == tenant.id
    assert draft.comment_id == comment.id
    assert draft.operator_id == user.id
    assert draft.status == "draft"


async def test_send_reply_uses_draft_and_marks_comment(db_session, monkeypatch):
    tenant, user, account, _target, comment = _seed_reply_context(db_session)
    draft = reply_service.create_draft(
        db_session,
        tenant_id=tenant.id,
        comment_id=comment.id,
        content="Reply from draft",
        user=user,
    )

    async def fake_send_reply(db, action, account_obj, comment_row, content):
        action.status = "sent"
        action.response_payload = {"ok": True}
        comment_row.is_replied = True
        comment_row.is_handled = True
        db.add(action)
        db.add(comment_row)
        db.commit()
        db.refresh(action)
        return action

    monkeypatch.setattr(reply_service.gateway, "send_reply", fake_send_reply)

    action = await reply_service.send_reply(
        db_session,
        tenant_id=tenant.id,
        account_id=account.id,
        comment_id=comment.id,
        content=None,
        draft_id=draft.id,
        user=user,
    )

    db_session.refresh(comment)
    db_session.refresh(draft)

    assert action.status == "sent"
    assert action.account_id == account.id
    assert action.comment_id == comment.id
    assert comment.is_replied is True
    assert comment.is_handled is True
    assert draft.status == "sent"

    actions = {
        row.action
        for row in db_session.scalars(select(AuditLog).where(AuditLog.tenant_id == tenant.id)).all()
    }
    assert "reply.draft.create" in actions
    assert "reply.send.requested" in actions
    assert "reply.send.completed" in actions


async def test_send_reply_failure_writes_failed_audit(db_session, monkeypatch):
    tenant, user, account, _target, comment = _seed_reply_context(db_session)
    draft = reply_service.create_draft(
        db_session,
        tenant_id=tenant.id,
        comment_id=comment.id,
        content="Reply from draft",
        user=user,
    )

    async def fake_send_reply(db, action, account_obj, comment_row, content):
        action.status = "failed"
        action.error_message = "risk control"
        db.add(action)
        db.commit()
        db.refresh(action)
        return action

    monkeypatch.setattr(reply_service.gateway, "send_reply", fake_send_reply)

    action = await reply_service.send_reply(
        db_session,
        tenant_id=tenant.id,
        account_id=account.id,
        comment_id=comment.id,
        content=None,
        draft_id=draft.id,
        user=user,
    )

    db_session.refresh(comment)
    db_session.refresh(draft)

    assert action.status == "failed"
    assert comment.is_replied is False
    assert comment.is_handled is False
    assert draft.status == "draft"

    actions = {
        row.action
        for row in db_session.scalars(select(AuditLog).where(AuditLog.tenant_id == tenant.id)).all()
    }
    assert "reply.send.failed" in actions
