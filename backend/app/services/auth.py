from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    optional_datetime,
    sha256_text,
    utcnow,
    verify_password,
)
from app.models.entities import RefreshToken, TenantMember, User
from app.schemas.auth import TenantMembershipOut, TokenResponse, UserOut
from app.services.audit import log_audit


def _load_user(db: Session, email: str) -> Optional[User]:
    stmt = (
        select(User)
        .where(User.email == email)
        .options(joinedload(User.memberships).joinedload(TenantMember.tenant))
    )
    return db.scalar(stmt)


def serialize_user(user: User) -> UserOut:
    memberships = []
    for member in user.memberships:
        if member.is_active and member.tenant:
            memberships.append(
                TenantMembershipOut(
                    tenant_id=member.tenant_id,
                    tenant_name=member.tenant.name,
                    tenant_slug=member.tenant.slug,
                    role=member.role,
                )
            )
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        memberships=memberships,
    )


def login(db: Session, email: str, password: str, user_agent: Optional[str] = None) -> TokenResponse:
    user = _load_user(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")

    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=sha256_text(refresh_token),
        expires_at=expires_at,
        user_agent=user_agent,
    )
    user.last_login_at = utcnow()
    db.add(refresh_record)
    log_audit(db, "auth.login", "user", entity_id=user.id, user=user, payload={"email": user.email})
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def refresh(db: Session, raw_refresh_token: str) -> TokenResponse:
    from app.core.security import decode_refresh_token

    try:
        payload = decode_refresh_token(raw_refresh_token)
        user_id = payload["sub"]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    token_hash = sha256_text(raw_refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    token = db.scalar(stmt)
    expires_at = optional_datetime(token.expires_at) if token else None
    revoked_at = optional_datetime(token.revoked_at) if token else None
    if token is None or revoked_at is not None or expires_at is None or expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User unavailable")

    token.revoked_at = utcnow()
    access_token = create_access_token(user.id)
    new_refresh_token, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=sha256_text(new_refresh_token),
            expires_at=expires_at,
            user_agent=token.user_agent,
        )
    )
    log_audit(db, "auth.refresh", "user", entity_id=user.id, user=user, payload={})
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


def logout(db: Session, raw_refresh_token: str, user: User) -> None:
    token_hash = sha256_text(raw_refresh_token)
    token = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token:
        token.revoked_at = utcnow()
    log_audit(db, "auth.logout", "user", entity_id=user.id, user=user, payload={})
    db.commit()
