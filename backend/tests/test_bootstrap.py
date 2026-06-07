from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.models.entities import Tenant, TenantMember, User
from app.services.bootstrap import bootstrap_defaults


def test_bootstrap_defaults_creates_owner_and_tenant(db_session) -> None:
    bootstrap_defaults(db_session)

    owner = db_session.scalar(select(User).where(User.email == settings.bootstrap_owner_email))
    tenant = db_session.scalar(select(Tenant).where(Tenant.slug == settings.bootstrap_tenant_slug))
    membership = db_session.scalar(
        select(TenantMember).where(TenantMember.user_id == owner.id, TenantMember.tenant_id == tenant.id)
    )

    assert owner is not None
    assert tenant is not None
    assert membership is not None
    assert membership.role == "owner"


def test_bootstrap_defaults_is_idempotent(db_session) -> None:
    bootstrap_defaults(db_session)
    bootstrap_defaults(db_session)

    owners = db_session.scalars(select(User).where(User.email == settings.bootstrap_owner_email)).all()
    tenants = db_session.scalars(select(Tenant).where(Tenant.slug == settings.bootstrap_tenant_slug)).all()
    memberships = db_session.scalars(select(TenantMember)).all()

    assert len(owners) == 1
    assert len(tenants) == 1
    assert len(memberships) == 1

