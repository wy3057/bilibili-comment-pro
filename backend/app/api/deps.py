from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.entities import Tenant, TenantMember, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class TenantContext:
    tenant: Tenant
    membership: TenantMember
    user: User


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = payload["sub"]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_tenant_context(
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    stmt = select(TenantMember).where(TenantMember.user_id == user.id, TenantMember.is_active.is_(True))
    memberships = db.scalars(stmt).all()
    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant access")

    membership = None
    if x_tenant_id:
        membership = next((item for item in memberships if item.tenant_id == x_tenant_id), None)
    elif len(memberships) == 1:
        membership = memberships[0]

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header required when user has multiple tenants",
        )

    tenant = db.get(Tenant, membership.tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant unavailable")

    return TenantContext(tenant=tenant, membership=membership, user=user)


def require_roles(*roles: str) -> Callable[[TenantContext], TenantContext]:
    def dependency(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        allowed = set(roles)
        if ctx.membership.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return ctx

    return dependency


OWNER_OR_ADMIN = require_roles(UserRole.owner.value, UserRole.admin.value)
OPERATOR_OR_HIGHER = require_roles(
    UserRole.owner.value,
    UserRole.admin.value,
    UserRole.operator.value,
)

