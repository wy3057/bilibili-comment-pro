from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.core.config import settings
from app.core.metrics import TARGETS_SCHEDULED_TOTAL
from app.db.session import SessionLocal
from app.models.entities import (
    AccountStatus,
    BilibiliAccount,
    DouyinAccount,
    DouyinPersonalAccount,
    DouyinPersonalTarget,
    DouyinTarget,
    MonitorTarget,
)
from app.services import douyin as douyin_service
from app.services import douyin_personal as douyin_personal_service
from app.services.bilibili_gateway import gateway
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def should_poll_target(target: MonitorTarget, now: Optional[datetime] = None) -> bool:
    now = now or _utcnow()
    if target.status != "active":
        return False
    if target.last_polled_at is None:
        return True
    elapsed = (now - target.last_polled_at).total_seconds()
    return elapsed >= target.poll_interval


def should_refresh_douyin_account(account: DouyinAccount, now: Optional[datetime] = None) -> bool:
    now = now or _utcnow()
    if account.status != AccountStatus.active.value:
        return True
    if account.access_token_expires_at is None:
        return False
    expires_at = (
        account.access_token_expires_at.replace(tzinfo=timezone.utc)
        if account.access_token_expires_at.tzinfo is None
        else account.access_token_expires_at.astimezone(timezone.utc)
    )
    return expires_at <= now + timedelta(hours=12)


def should_refresh_douyin_personal_account(account: DouyinPersonalAccount, now: Optional[datetime] = None) -> bool:
    now = now or _utcnow()
    if account.status != AccountStatus.active.value:
        return True
    if account.last_validated_at is None:
        return True
    validated_at = (
        account.last_validated_at.replace(tzinfo=timezone.utc)
        if account.last_validated_at.tzinfo is None
        else account.last_validated_at.astimezone(timezone.utc)
    )
    return validated_at <= now - timedelta(hours=12)


@celery_app.task(name="app.workers.tasks.poll_target")
def poll_target(target_id: str) -> dict:
    db = SessionLocal()
    try:
        target = db.get(MonitorTarget, target_id)
        if target is None or not should_poll_target(target):
            return {"skipped": True}
        result = asyncio.run(gateway.poll_target_comments(db, target))
        return result
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.poll_active_targets")
def poll_active_targets() -> dict:
    db = SessionLocal()
    try:
        targets = db.scalars(select(MonitorTarget).where(MonitorTarget.status == "active")).all()
        douyin_targets = db.scalars(select(DouyinTarget).where(DouyinTarget.status == "active")).all()
        douyin_personal_targets = db.scalars(
            select(DouyinPersonalTarget).where(DouyinPersonalTarget.status == "active")
        ).all()
        scheduled = 0
        for target in targets:
            if should_poll_target(target):
                poll_target.delay(target.id)
                scheduled += 1
                TARGETS_SCHEDULED_TOTAL.inc()
        for target in douyin_targets:
            if should_poll_target(target):
                asyncio.run(douyin_service.gateway.poll_target_comments(db, target))
                scheduled += 1
                TARGETS_SCHEDULED_TOTAL.inc()
        for target in douyin_personal_targets:
            if settings.douyin_personal_enabled and should_poll_target(target):
                asyncio.run(douyin_personal_service.gateway.poll_target_comments(db, target))
                scheduled += 1
                TARGETS_SCHEDULED_TOTAL.inc()
        return {"scheduled": scheduled}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.refresh_accounts")
def refresh_accounts() -> dict:
    db = SessionLocal()
    refreshed = 0
    try:
        accounts = db.scalars(select(BilibiliAccount).where(BilibiliAccount.status != AccountStatus.disabled.value)).all()
        for account in accounts:
            asyncio.run(gateway.refresh_account(db, account))
            refreshed += 1
        douyin_accounts = db.scalars(select(DouyinAccount).where(DouyinAccount.status != AccountStatus.disabled.value)).all()
        for account in douyin_accounts:
            if should_refresh_douyin_account(account):
                asyncio.run(douyin_service.gateway.refresh_account(db, account))
                refreshed += 1
        douyin_personal_accounts = db.scalars(
            select(DouyinPersonalAccount).where(DouyinPersonalAccount.status != AccountStatus.disabled.value)
        ).all()
        for account in douyin_personal_accounts:
            if settings.douyin_personal_enabled and should_refresh_douyin_personal_account(account):
                asyncio.run(douyin_personal_service.refresh_runtime(db, account, user=None))
                refreshed += 1
        return {"refreshed": refreshed}
    finally:
        db.close()
