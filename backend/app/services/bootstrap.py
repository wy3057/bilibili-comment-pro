from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.entities import Tenant, TenantMember, User, UserRole


def bootstrap_defaults(db: Session) -> None:
    owner = db.scalar(select(User).where(User.email == settings.bootstrap_owner_email))
    if owner is None:
        owner = User(
            email=settings.bootstrap_owner_email,
            display_name=settings.bootstrap_owner_name,
            password_hash=hash_password(settings.bootstrap_owner_password),
            is_active=True,
        )
        db.add(owner)
        db.flush()

    tenant = db.scalar(select(Tenant).where(Tenant.slug == settings.bootstrap_tenant_slug))
    if tenant is None:
        tenant = Tenant(
            name=settings.bootstrap_tenant_name,
            slug=settings.bootstrap_tenant_slug,
            description="Bootstrapped tenant",
            is_active=True,
        )
        db.add(tenant)
        db.flush()

    membership = db.scalar(
        select(TenantMember).where(TenantMember.tenant_id == tenant.id, TenantMember.user_id == owner.id)
    )
    if membership is None:
        db.add(
            TenantMember(
                tenant_id=tenant.id,
                user_id=owner.id,
                role=UserRole.owner.value,
                is_active=True,
            )
        )
    db.commit()

