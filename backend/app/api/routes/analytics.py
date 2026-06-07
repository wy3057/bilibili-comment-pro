from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import OPERATOR_OR_HIGHER, TenantContext
from app.db.session import get_db
from app.schemas.analytics import AccountHealthItem, OverviewStats, ReplyPerformancePoint, TrendPoint
from app.services import analytics as analytics_service

router = APIRouter()


@router.get("/overview", response_model=OverviewStats)
def overview(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> OverviewStats:
    return analytics_service.get_overview(db, ctx.tenant.id)


@router.get("/comments/trends", response_model=list[TrendPoint])
def comment_trends(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[TrendPoint]:
    return analytics_service.get_trends(db, ctx.tenant.id)


@router.get("/replies/performance", response_model=list[ReplyPerformancePoint])
def reply_performance(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[ReplyPerformancePoint]:
    return analytics_service.get_reply_performance(db, ctx.tenant.id)


@router.get("/accounts/health", response_model=list[AccountHealthItem])
def account_health(
    ctx: TenantContext = Depends(OPERATOR_OR_HIGHER),
    db: Session = Depends(get_db),
) -> list[AccountHealthItem]:
    return analytics_service.get_account_health(db, ctx.tenant.id)
