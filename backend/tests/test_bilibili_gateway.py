from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.models.entities import AccountStatus, BilibiliAccount, CommentEvent, CommentEventType, MonitorTarget, RiskStatus, Tenant
from app.services.bilibili_gateway import BilibiliGateway


def _seed_gateway_context(db_session):
    tenant = Tenant(name="Tenant Gateway", slug="tenant-gateway", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    account = BilibiliAccount(
        tenant_id=tenant.id,
        uid=61001,
        username="gateway-account",
        status=AccountStatus.active.value,
        risk_status=RiskStatus.normal.value,
    )
    db_session.add(account)
    db_session.flush()

    target = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=456789,
        bvid="BV1gateway1",
        title="Gateway Target",
        poll_interval=300,
        status="active",
    )
    db_session.add(target)
    db_session.commit()
    db_session.refresh(account)
    db_session.refresh(target)
    return account, target


def _raw_comment(*, rpid: int, message: str, like_count: int, parent: Optional[int] = None, root: Optional[int] = None):
    return {
        "rpid": rpid,
        "root": root,
        "parent": parent,
        "ctime": int(datetime.now(timezone.utc).timestamp()),
        "like": like_count,
        "member": {"mid": 9001, "uname": "Alice"},
        "content": {"message": message},
    }


def test_upsert_comment_creates_discovered_and_updated_events(db_session):
    gateway = BilibiliGateway()
    account, target = _seed_gateway_context(db_session)

    created, payload = gateway._upsert_comment(
        db_session,
        target,
        account,
        _raw_comment(rpid=7001, message="hello", like_count=1),
        True,
        event_type=CommentEventType.discovered.value,
    )

    assert created == 1
    assert payload is not None

    created, payload = gateway._upsert_comment(
        db_session,
        target,
        account,
        _raw_comment(rpid=7001, message="hello updated", like_count=3),
        True,
        event_type=CommentEventType.discovered.value,
    )

    assert created == 0
    assert payload is None
    db_session.flush()

    events = list(
        db_session.scalars(select(CommentEvent).order_by(CommentEvent.created_at.asc(), CommentEvent.id.asc())).all()
    )
    assert len(events) == 2
    assert events[0].event_type == CommentEventType.discovered.value
    assert events[1].event_type == CommentEventType.updated.value
    assert events[1].payload["message"]["to"] == "hello updated"
    assert events[1].payload["like_count"]["to"] == 3


def test_upsert_comment_marks_hydrated_sub_replies(db_session):
    gateway = BilibiliGateway()
    account, target = _seed_gateway_context(db_session)

    created, payload = gateway._upsert_comment(
        db_session,
        target,
        account,
        _raw_comment(rpid=8001, message="nested hello", like_count=0, parent=7001, root=7001),
        False,
        event_type=CommentEventType.hydrated.value,
    )

    assert created == 1
    assert payload is not None
    db_session.flush()

    event = db_session.scalar(select(CommentEvent).where(CommentEvent.event_type == CommentEventType.hydrated.value))
    assert event is not None
    assert event.payload["message"] == "nested hello"
