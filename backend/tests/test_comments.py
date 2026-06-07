from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.entities import AccountStatus, AuditLog, BilibiliAccount, Comment, MonitorTarget, RiskStatus, Tenant, User
from app.services import comments as comment_service


def _seed_comment_context(db_session):
    tenant = Tenant(name="Tenant Comments", slug="tenant-comments", is_active=True)
    user = User(email="comments@example.com", display_name="Comments User", password_hash="hash", is_active=True)
    db_session.add_all([tenant, user])
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(user)

    account = BilibiliAccount(
        tenant_id=tenant.id,
        uid=71001,
        username="comments-account",
        status=AccountStatus.active.value,
        risk_status=RiskStatus.normal.value,
    )
    db_session.add(account)
    db_session.flush()

    target = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=111222,
        bvid="BV1comments1",
        title="Comments Target",
        poll_interval=300,
        status="active",
    )
    db_session.add(target)
    db_session.flush()

    comment = Comment(
        tenant_id=tenant.id,
        target_id=target.id,
        account_id=account.id,
        rpid=8801,
        root_rpid=8801,
        parent_rpid=None,
        oid=target.oid,
        member_mid=42,
        member_name="Alice",
        message="Handle me",
        posted_at=datetime.now(timezone.utc),
        like_count=0,
        is_top_level=True,
        raw_payload={"source": "test"},
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return tenant, user, comment


def test_mark_comments_handled_only_counts_real_changes_and_writes_audit(db_session):
    tenant, user, comment = _seed_comment_context(db_session)

    updated = comment_service.mark_comments_handled(
        db_session,
        tenant.id,
        [comment.id],
        True,
        user,
    )

    assert updated == 1

    updated_again = comment_service.mark_comments_handled(
        db_session,
        tenant.id,
        [comment.id],
        True,
        user,
    )

    assert updated_again == 0

    audits = list(
        db_session.scalars(select(AuditLog).where(AuditLog.action == "comment.handle.update")).all()
    )
    assert len(audits) == 1
    assert audits[0].payload["comment_ids"] == [comment.id]
