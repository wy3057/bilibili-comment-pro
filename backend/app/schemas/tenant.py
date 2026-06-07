from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class TenantCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class TenantOut(ORMModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    is_active: bool


class TenantMemberCreate(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    password: Optional[str] = None
    role: str


class TenantMemberUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class TenantMemberOut(ORMModel):
    id: str
    tenant_id: str
    user_id: str
    role: str
    is_active: bool
    user_email: EmailStr
    user_display_name: str
