from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.entities import TenantMember, User
from app.services.realtime import manager

router = APIRouter()


@router.websocket("/ws/{tenant_id}")
async def tenant_stream(websocket: WebSocket, tenant_id: str, token: str) -> None:
    db = SessionLocal()
    try:
        try:
            payload = decode_access_token(token)
            user_id = payload["sub"]
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user = db.get(User, user_id)
        membership = db.scalar(
            select(TenantMember).where(
                TenantMember.tenant_id == tenant_id,
                TenantMember.user_id == user_id,
                TenantMember.is_active.is_(True),
            )
        )
        if user is None or not user.is_active or membership is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect(tenant_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect(tenant_id, websocket)
    finally:
        db.close()
