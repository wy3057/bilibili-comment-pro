from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import hash_password
from app.models.entities import Tenant, TenantMember, User, UserRole
from app.schemas.tenant import TenantCreate, TenantMemberOut
from app.services.audit import log_audit


def list_tenants_for_user(db: Session, user: User) -> List[Tenant]:
    stmt = (
        select(Tenant)
        .join(TenantMember, TenantMember.tenant_id == Tenant.id)
        .where(TenantMember.user_id == user.id, TenantMember.is_active.is_(True))
        .order_by(Tenant.name.asc())
    )
    return list(db.scalars(stmt).all())


def create_tenant(db: Session, user: User, payload: TenantCreate) -> Tenant:
    existing = db.scalar(select(Tenant).where((Tenant.name == payload.name) | (Tenant.slug == payload.slug)))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant name or slug already exists")

    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        is_active=True,
    )
    db.add(tenant)
    db.flush()
    db.add(TenantMember(tenant_id=tenant.id, user_id=user.id, role=UserRole.owner.value, is_active=True))
    log_audit(db, "tenant.create", "tenant", tenant.id, user=user, payload=payload.model_dump())
    db.commit()
    db.refresh(tenant)
    return tenant


def list_members(db: Session, tenant_id: str) -> List[TenantMember]:
    stmt = (
        select(TenantMember)
        .where(TenantMember.tenant_id == tenant_id)
        .options(joinedload(TenantMember.user))
        .order_by(TenantMember.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def member_to_schema(member: TenantMember) -> TenantMemberOut:
    return TenantMemberOut(
        id=member.id,
        tenant_id=member.tenant_id,
        user_id=member.user_id,
        role=member.role,
        is_active=member.is_active,
        user_email=member.user.email,
        user_display_name=member.user.display_name,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


def create_member(
    db: Session,
    tenant_id: str,
    email: str,
    display_name: Optional[str],
    password: Optional[str],
    role: str,
    actor: User,
) -> TenantMember:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        if not password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password required for new user")
        user = User(
            email=email,
            display_name=display_name or email.split("@")[0],
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.flush()

    existing = db.scalar(
        select(TenantMember).where(TenantMember.tenant_id == tenant_id, TenantMember.user_id == user.id)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already exists")

    member = TenantMember(tenant_id=tenant_id, user_id=user.id, role=role, is_active=True)
    db.add(member)
    log_audit(
        db,
        "tenant.member.create",
        "tenant_member",
        tenant_id=tenant_id,
        user=actor,
        payload={"email": email, "role": role},
    )
    db.commit()
    db.refresh(member)
    return member


def update_member(
    db: Session,
    member: TenantMember,
    role: Optional[str],
    is_active: Optional[bool],
    actor: User,
) -> TenantMember:
    if role is not None:
        member.role = role
    if is_active is not None:
        member.is_active = is_active
    log_audit(
        db,
        "tenant.member.update",
        "tenant_member",
        entity_id=member.id,
        tenant_id=member.tenant_id,
        user=actor,
        payload={"role": member.role, "is_active": member.is_active},
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
