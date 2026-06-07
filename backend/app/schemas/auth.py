from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TenantMembershipOut(BaseModel):
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    role: str


class UserOut(ORMModel):
    id: str
    email: EmailStr
    display_name: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    memberships: List[TenantMembershipOut]
