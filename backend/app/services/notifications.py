from __future__ import annotations

import logging
from typing import Iterable, List

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_payload, encrypt_payload
from app.core.metrics import NOTIFICATION_DELIVERIES_TOTAL
from app.models.entities import TenantWebhookConfig, User
from app.schemas.webhook import WebhookConfigCreate, WebhookConfigUpdate, WebhookTestResult
from app.services.audit import log_audit

logger = logging.getLogger(__name__)


def list_webhooks(db: Session, tenant_id: str) -> List[TenantWebhookConfig]:
    stmt = (
        select(TenantWebhookConfig)
        .where(TenantWebhookConfig.tenant_id == tenant_id)
        .order_by(TenantWebhookConfig.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_webhook(
    db: Session,
    tenant_id: str,
    payload: WebhookConfigCreate,
    actor: User,
) -> TenantWebhookConfig:
    webhook = TenantWebhookConfig(
        tenant_id=tenant_id,
        name=payload.name,
        provider=payload.provider,
        encrypted_webhook_url=encrypt_payload({"url": payload.webhook_url}),
        is_enabled=payload.is_enabled,
    )
    db.add(webhook)
    db.flush()
    log_audit(
        db,
        "notification.webhook.create",
        "tenant_webhook_config",
        entity_id=webhook.id,
        tenant_id=tenant_id,
        user=actor,
        payload={"name": payload.name, "provider": payload.provider, "is_enabled": payload.is_enabled},
    )
    db.commit()
    db.refresh(webhook)
    return webhook


def update_webhook(
    db: Session,
    webhook: TenantWebhookConfig,
    payload: WebhookConfigUpdate,
    actor: User,
) -> TenantWebhookConfig:
    if payload.name is not None:
        webhook.name = payload.name
    if payload.provider is not None:
        webhook.provider = payload.provider
    if payload.webhook_url is not None:
        webhook.encrypted_webhook_url = encrypt_payload({"url": payload.webhook_url})
    if payload.is_enabled is not None:
        webhook.is_enabled = payload.is_enabled
    db.add(webhook)
    log_audit(
        db,
        "notification.webhook.update",
        "tenant_webhook_config",
        entity_id=webhook.id,
        tenant_id=webhook.tenant_id,
        user=actor,
        payload=payload.model_dump(exclude_none=True),
    )
    db.commit()
    db.refresh(webhook)
    return webhook


def delete_webhook(db: Session, webhook: TenantWebhookConfig, actor: User) -> None:
    log_audit(
        db,
        "notification.webhook.delete",
        "tenant_webhook_config",
        entity_id=webhook.id,
        tenant_id=webhook.tenant_id,
        user=actor,
        payload={"name": webhook.name},
    )
    db.delete(webhook)
    db.commit()


def decrypt_webhook_url(webhook: TenantWebhookConfig) -> str:
    payload = decrypt_payload(webhook.encrypted_webhook_url)
    return payload["url"]


async def test_webhook(db: Session, webhook: TenantWebhookConfig, actor: User) -> WebhookTestResult:
    detail = await send_text_notification(
        webhook=webhook,
        text="Bilibili Comment Platform webhook 测试消息。",
    )
    log_audit(
        db,
        "notification.webhook.test",
        "tenant_webhook_config",
        entity_id=webhook.id,
        tenant_id=webhook.tenant_id,
        user=actor,
        payload={"detail": detail},
    )
    db.commit()
    return WebhookTestResult(ok=True, detail=detail)


async def notify_new_comments(
    db: Session,
    tenant_id: str,
    target_title: str,
    comments: Iterable[dict],
) -> None:
    comments = list(comments)
    if not comments:
        return

    webhooks = [item for item in list_webhooks(db, tenant_id) if item.is_enabled]
    if not webhooks:
        return

    header = "🔥【%s】发现 %s 条新评论" % (target_title, len(comments))
    lines = [header, "-" * 24]
    for item in comments:
        lines.append("用户: %s" % item["member_name"])
        lines.append("类型: %s" % ("主评论" if item["is_top_level"] else "楼中楼"))
        lines.append("内容: %s" % item["message"])
        lines.append("时间: %s" % item["posted_at"])
        lines.append("-" * 24)
    text = "\n".join(lines)

    for webhook in webhooks:
        try:
            await send_text_notification(webhook, text)
        except Exception as exc:
            NOTIFICATION_DELIVERIES_TOTAL.labels(webhook.provider.lower(), "failed").inc()
            logger.warning(
                "Webhook notification failed",
                extra={
                    "tenant_id": tenant_id,
                    "webhook_id": webhook.id,
                    "provider": webhook.provider,
                    "error": str(exc),
                },
            )


async def send_text_notification(webhook: TenantWebhookConfig, text: str) -> str:
    url = decrypt_webhook_url(webhook)
    provider = webhook.provider.lower()
    if provider in {"slack", "discord"}:
        payload = {"content": text}
    else:
        payload = {
            "msgtype": "text",
            "text": {
                "content": text,
            },
        }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
    NOTIFICATION_DELIVERIES_TOTAL.labels(provider, "success").inc()
    return "sent via %s" % webhook.provider
