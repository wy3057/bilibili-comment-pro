from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import BilibiliAccount, MonitorTarget, User
from app.schemas.target import ImportedTargetCandidate, TargetCreate, TargetUpdate
from app.services.audit import log_audit
from app.services.bilibili_gateway import gateway


def list_targets(db: Session, tenant_id: str) -> List[MonitorTarget]:
    stmt = select(MonitorTarget).where(MonitorTarget.tenant_id == tenant_id).order_by(MonitorTarget.created_at.desc())
    return list(db.scalars(stmt).all())


def create_target(
    db: Session, tenant_id: str, payload: TargetCreate, user: Optional[User] = None
) -> MonitorTarget:
    account = db.get(BilibiliAccount, payload.account_id)
    if not account or account.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    existing = db.scalar(
        select(MonitorTarget).where(MonitorTarget.tenant_id == tenant_id, MonitorTarget.bvid == payload.bvid)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target already exists")
    target = MonitorTarget(
        tenant_id=tenant_id,
        account_id=payload.account_id,
        oid=payload.oid,
        bvid=payload.bvid,
        title=payload.title,
        owner_mid=payload.owner_mid,
        poll_interval=payload.poll_interval,
        status="active",
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    log_audit(
        db,
        "target.create",
        "monitor_target",
        entity_id=target.id,
        tenant_id=tenant_id,
        user=user,
        payload=payload.model_dump(),
    )
    db.commit()
    return target


def update_target(
    db: Session, target: MonitorTarget, payload: TargetUpdate, user: Optional[User] = None
) -> MonitorTarget:
    changes: dict[str, object] = {}
    if payload.status is not None:
        changes["status"] = {"from": target.status, "to": payload.status}
        target.status = payload.status
    if payload.poll_interval is not None:
        changes["poll_interval"] = {"from": target.poll_interval, "to": payload.poll_interval}
        target.poll_interval = payload.poll_interval
    if payload.title is not None:
        changes["title"] = {"from": target.title, "to": payload.title}
        target.title = payload.title
    db.add(target)
    db.commit()
    db.refresh(target)
    if changes:
        log_audit(
            db,
            "target.update",
            "monitor_target",
            entity_id=target.id,
            tenant_id=target.tenant_id,
            user=user,
            payload=changes,
        )
        db.commit()
    return target


def delete_target(db: Session, target: MonitorTarget, user: Optional[User] = None) -> None:
    log_audit(
        db,
        "target.delete",
        "monitor_target",
        entity_id=target.id,
        tenant_id=target.tenant_id,
        user=user,
        payload={"bvid": target.bvid, "title": target.title},
    )
    db.delete(target)
    db.commit()


async def preview_import_candidates(
    db: Session,
    tenant_id: str,
    account: BilibiliAccount,
) -> List[ImportedTargetCandidate]:
    items = await gateway.import_video_targets(account)
    existing_bvids = {
        row.bvid
        for row in db.scalars(select(MonitorTarget).where(MonitorTarget.tenant_id == tenant_id)).all()
    }

    candidates: List[ImportedTargetCandidate] = []
    for item in items:
        candidates.append(
            ImportedTargetCandidate(
                oid=item["oid"],
                bvid=item["bvid"],
                title=item["title"],
                owner_mid=item.get("owner_mid"),
                already_monitored=item["bvid"] in existing_bvids,
            )
        )
    return candidates


async def import_selected_candidates(
    db: Session,
    tenant_id: str,
    account: BilibiliAccount,
    selected_bvids: Optional[List[str]],
    only_missing: bool,
    poll_interval: int,
    user: Optional[User] = None,
) -> List[MonitorTarget]:
    items = await gateway.import_video_targets(account)
    existing_bvids = {
        row.bvid
        for row in db.scalars(select(MonitorTarget).where(MonitorTarget.tenant_id == tenant_id)).all()
    }

    selected = set(selected_bvids or [])
    created: List[MonitorTarget] = []
    skipped_existing_bvids: List[str] = []
    for item in items:
        bvid = item["bvid"]
        if selected and bvid not in selected:
            continue
        if bvid in existing_bvids:
            skipped_existing_bvids.append(bvid)
            continue
        target = MonitorTarget(
            tenant_id=tenant_id,
            account_id=account.id,
            oid=item["oid"],
            bvid=bvid,
            title=item["title"],
            owner_mid=item.get("owner_mid"),
            poll_interval=poll_interval,
            status="active",
        )
        db.add(target)
        db.flush()
        existing_bvids.add(bvid)
        created.append(target)
    log_audit(
        db,
        "target.import",
        "monitor_target",
        tenant_id=tenant_id,
        user=user,
        payload={
            "account_id": account.id,
            "only_missing": only_missing,
            "poll_interval": poll_interval,
            "selected_bvids": sorted(selected) if selected else None,
            "created_bvids": [target.bvid for target in created],
            "skipped_existing_bvids": skipped_existing_bvids,
        },
    )
    db.commit()
    return created
