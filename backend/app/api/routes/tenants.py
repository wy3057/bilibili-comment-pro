from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import OWNER_OR_ADMIN, TenantContext, get_current_user, get_tenant_context
from app.db.session import get_db
from app.models.entities import TenantMember, User
from app.schemas.tenant import (
    TenantCreate,
    TenantMemberCreate,
    TenantMemberOut,
    TenantMemberUpdate,
    TenantOut,
)
from app.services import tenants as tenant_service

router = APIRouter()


@router.get("", response_model=list[TenantOut])
def list_tenants(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[TenantOut]:
    return tenant_service.list_tenants_for_user(db, user)


@router.post("", response_model=TenantOut)
def create_tenant(
    payload: TenantCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> TenantOut:
    return tenant_service.create_tenant(db, user, payload)


@router.get("/{tenant_id}/members", response_model=list[TenantMemberOut])
def list_members(
    tenant_id: str,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> list[TenantMemberOut]:
    if tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return [tenant_service.member_to_schema(row) for row in tenant_service.list_members(db, tenant_id)]


@router.post("/{tenant_id}/members", response_model=TenantMemberOut)
def create_member(
    tenant_id: str,
    payload: TenantMemberCreate,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> TenantMemberOut:
    if tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    member = tenant_service.create_member(
        db,
        tenant_id=tenant_id,
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        role=payload.role,
        actor=ctx.user,
    )
    db.refresh(member, ["user"])
    return tenant_service.member_to_schema(member)


@router.patch("/{tenant_id}/members/{member_id}", response_model=TenantMemberOut)
def update_member(
    tenant_id: str,
    member_id: str,
    payload: TenantMemberUpdate,
    ctx: TenantContext = Depends(OWNER_OR_ADMIN),
    db: Session = Depends(get_db),
) -> TenantMemberOut:
    if tenant_id != ctx.tenant.id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    member = db.get(TenantMember, member_id)
    if member is None or member.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Member not found")
    member = tenant_service.update_member(db, member, payload.role, payload.is_active, ctx.user)
    db.refresh(member, ["user"])
    return tenant_service.member_to_schema(member)

