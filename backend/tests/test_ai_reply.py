from __future__ import annotations

from datetime import datetime, timezone

from app.models.entities import AccountStatus, AIReplyMode, BilibiliAccount, Comment, MonitorTarget, RiskStatus, Tenant, User
from app.services import ai_reply as ai_reply_service
from app.services import ops as ops_service


def _seed_ai_context(db_session):
    tenant = Tenant(name="Tenant AI", slug="tenant-ai", is_active=True)
    user = User(email="ai@example.com", display_name="AI User", password_hash="hash", is_active=True)
    db_session.add_all([tenant, user])
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(user)

    account = BilibiliAccount(
        tenant_id=tenant.id,
        uid=70001,
        username="ai-account",
        status=AccountStatus.active.value,
        risk_status=RiskStatus.normal.value,
    )
    db_session.add(account)
    db_session.flush()

    target = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=112233,
        bvid="BV1ai11111",
        title="AI Target",
        poll_interval=300,
        status="active",
    )
    db_session.add(target)
    db_session.flush()

    comment = Comment(
        tenant_id=tenant.id,
        target_id=target.id,
        account_id=account.id,
        rpid=9901,
        root_rpid=9901,
        parent_rpid=None,
        oid=target.oid,
        member_mid=11,
        member_name="Alice",
        message="How does this work?",
        posted_at=datetime.now(timezone.utc),
        like_count=0,
        is_top_level=True,
        raw_payload={"source": "test"},
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return tenant, user, comment


def test_ai_reply_status_has_expected_shape():
    status = ai_reply_service.get_ai_reply_status()
    assert set(status.keys()) == {"enabled", "provider", "model", "base_url", "api_mode", "mode"}


async def test_ops_generate_reply_suggestion_uses_ai_service(db_session, monkeypatch):
    tenant, user, comment = _seed_ai_context(db_session)

    async def fake_generate_reply_suggestion(**kwargs):
        assert kwargs["platform"] == "bilibili"
        assert kwargs["author_name"] == "Alice"
        assert kwargs["content"] == "How does this work?"
        assert kwargs["target_title"] == "AI Target"
        return "Thanks for your question. We'll look into it."

    monkeypatch.setattr(ai_reply_service, "generate_reply_suggestion", fake_generate_reply_suggestion)

    content = await ops_service.generate_reply_suggestion(
        db_session,
        tenant.id,
        platform="bilibili",
        comment_id=comment.id,
        account_id=comment.account_id,
        extra_instruction="Keep it concise.",
        user=user,
    )

    assert content == ("Thanks for your question. We'll look into it.", False)


def test_ai_reply_mode_defaults_and_can_update(db_session):
    tenant, _user, _comment = _seed_ai_context(db_session)

    assert ai_reply_service.get_tenant_ai_reply_mode(db_session, tenant.id) == AIReplyMode.manual_review.value

    updated = ai_reply_service.update_tenant_ai_reply_mode(db_session, tenant.id, AIReplyMode.direct_send.value)
    assert updated == AIReplyMode.direct_send.value
    assert ai_reply_service.get_tenant_ai_reply_mode(db_session, tenant.id) == AIReplyMode.direct_send.value
