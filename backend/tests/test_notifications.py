from __future__ import annotations

from sqlalchemy import select

from app.core.crypto import decrypt_payload
from app.models.entities import Tenant, TenantWebhookConfig, User
from app.schemas.webhook import WebhookConfigCreate, WebhookConfigUpdate
from app.services import notifications as notification_service


def _make_actor(db_session):
    tenant = Tenant(name="Tenant A", slug="tenant-a", is_active=True)
    user = User(email="user@example.com", display_name="User", password_hash="hash", is_active=True)
    db_session.add_all([tenant, user])
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(user)
    return tenant, user


def test_create_and_update_webhook(db_session):
    tenant, actor = _make_actor(db_session)
    created = notification_service.create_webhook(
        db_session,
        tenant_id=tenant.id,
        payload=WebhookConfigCreate(
            name="primary",
            provider="dingtalk",
            webhook_url="https://example.com/a",
            is_enabled=True,
        ),
        actor=actor,
    )
    assert created.id
    decrypted = decrypt_payload(created.encrypted_webhook_url)
    assert decrypted["url"] == "https://example.com/a"

    updated = notification_service.update_webhook(
        db_session,
        created,
        WebhookConfigUpdate(name="renamed", is_enabled=False, webhook_url="https://example.com/b"),
        actor,
    )
    assert updated.name == "renamed"
    assert updated.is_enabled is False
    assert decrypt_payload(updated.encrypted_webhook_url)["url"] == "https://example.com/b"


async def test_notify_new_comments_only_hits_enabled_webhooks(db_session, monkeypatch):
    tenant, actor = _make_actor(db_session)
    enabled = notification_service.create_webhook(
        db_session,
        tenant.id,
        WebhookConfigCreate(
            name="enabled",
            provider="dingtalk",
            webhook_url="https://example.com/enabled",
            is_enabled=True,
        ),
        actor,
    )
    notification_service.create_webhook(
        db_session,
        tenant.id,
        WebhookConfigCreate(
            name="disabled",
            provider="dingtalk",
            webhook_url="https://example.com/disabled",
            is_enabled=False,
        ),
        actor,
    )

    calls = []

    async def fake_send_text_notification(webhook, text):
        calls.append((webhook.name, text))
        return "ok"

    monkeypatch.setattr(notification_service, "send_text_notification", fake_send_text_notification)

    await notification_service.notify_new_comments(
        db_session,
        tenant.id,
        "Video Title",
        [
            {
                "member_name": "Alice",
                "message": "hello",
                "posted_at": "2026-06-06 19:10:00",
                "is_top_level": True,
            }
        ],
    )

    assert calls
    assert calls[0][0] == "enabled"
    assert "Video Title" in calls[0][1]
    assert "Alice" in calls[0][1]
    assert "hello" in calls[0][1]


async def test_notify_new_comments_tolerates_webhook_failures(db_session, monkeypatch):
    tenant, actor = _make_actor(db_session)
    notification_service.create_webhook(
        db_session,
        tenant.id,
        WebhookConfigCreate(
            name="failing",
            provider="dingtalk",
            webhook_url="https://example.com/fail",
            is_enabled=True,
        ),
        actor,
    )
    notification_service.create_webhook(
        db_session,
        tenant.id,
        WebhookConfigCreate(
            name="working",
            provider="slack",
            webhook_url="https://example.com/ok",
            is_enabled=True,
        ),
        actor,
    )

    calls = []

    async def fake_send_text_notification(webhook, text):
        calls.append(webhook.name)
        if webhook.name == "failing":
            raise RuntimeError("boom")
        return "ok"

    monkeypatch.setattr(notification_service, "send_text_notification", fake_send_text_notification)

    await notification_service.notify_new_comments(
        db_session,
        tenant.id,
        "Video Title",
        [{"member_name": "Bob", "message": "hi", "posted_at": "2026-06-06 19:10:00", "is_top_level": True}],
    )

    assert sorted(calls) == ["failing", "working"]


async def test_test_webhook_returns_detail(db_session, monkeypatch):
    tenant, actor = _make_actor(db_session)
    webhook = notification_service.create_webhook(
        db_session,
        tenant.id,
        WebhookConfigCreate(
            name="primary",
            provider="slack",
            webhook_url="https://example.com/slack",
            is_enabled=True,
        ),
        actor,
    )

    async def fake_send_text_notification(webhook, text):
        return "sent via %s" % webhook.provider

    monkeypatch.setattr(notification_service, "send_text_notification", fake_send_text_notification)
    result = await notification_service.test_webhook(db_session, webhook, actor)
    assert result.ok is True
    assert result.detail == "sent via slack"
