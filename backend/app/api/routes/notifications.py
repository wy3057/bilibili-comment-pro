from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import OWNER_OR_ADMIN, TenantContext
from app.db.session import get_db
from app.models.entities import TenantWebhookConfig
from app.schemas.webhook import (
    WebhookConfigCreate,
    WebhookConfigOut,
    WebhookConfigUpdate,
    WebhookTestResult,
)
from app.services import notifications as notification_service

router = APIRouter()


@router.get("/webhooks", response_model=list[WebhookConfigOut])
def list_webhooks(
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> list[WebhookConfigOut]:
    return notification_service.list_webhooks(db, ctx.tenant.id)


@router.post("/webhooks", response_model=WebhookConfigOut)
def create_webhook(
    payload: WebhookConfigCreate,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> WebhookConfigOut:
    return notification_service.create_webhook(db, ctx.tenant.id, payload, ctx.user)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookConfigOut)
def update_webhook(
    webhook_id: str,
    payload: WebhookConfigUpdate,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> WebhookConfigOut:
    webhook = db.get(TenantWebhookConfig, webhook_id)
    if webhook is None or webhook.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return notification_service.update_webhook(db, webhook, payload, ctx.user)


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> dict:
    webhook = db.get(TenantWebhookConfig, webhook_id)
    if webhook is None or webhook.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    notification_service.delete_webhook(db, webhook, ctx.user)
    return {"message": "Deleted"}


@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResult)
async def test_webhook(
    webhook_id: str,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> WebhookTestResult:
    webhook = db.get(TenantWebhookConfig, webhook_id)
    if webhook is None or webhook.tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return await notification_service.test_webhook(db, webhook, ctx.user)

