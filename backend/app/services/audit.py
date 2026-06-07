from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


def log_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user: Optional[User] = None,
    payload: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    audit = AuditLog(
        tenant_id=tenant_id,
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload or {},
        ip_address=ip_address,
    )
    db.add(audit)
    db.flush()
    return audit

