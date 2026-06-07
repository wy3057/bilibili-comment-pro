from fastapi import APIRouter

from app.api.routes import (
    analytics,
    audit_logs,
    auth,
    bilibili,
    comments,
    douyin,
    douyin_personal,
    notifications,
    ops,
    reply_drafts,
    replies,
    system,
    targets,
    tenants,
    websocket,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(bilibili.router, prefix="/bilibili", tags=["bilibili"])
api_router.include_router(douyin.router, prefix="/douyin", tags=["douyin"])
api_router.include_router(douyin_personal.router, prefix="/douyin/personal", tags=["douyin-personal"])
api_router.include_router(ops.router, prefix="/ops", tags=["ops"])
api_router.include_router(targets.router, prefix="/targets", tags=["targets"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(reply_drafts.router, prefix="/reply-drafts", tags=["reply-drafts"])
api_router.include_router(replies.router, prefix="/reply-actions", tags=["replies"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(websocket.router, tags=["websocket"])
