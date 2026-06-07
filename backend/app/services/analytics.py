from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import DefaultDict, Dict, List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.entities import (
    BilibiliAccount,
    Comment,
    DouyinAccount,
    DouyinComment,
    DouyinPersonalAccount,
    DouyinPersonalComment,
    DouyinPersonalReplyAction,
    DouyinPersonalTarget,
    DouyinReplyAction,
    DouyinTarget,
    MonitorTarget,
    ReplyAction,
    ReplyActionStatus,
    TaskRun,
)
from app.schemas.analytics import AccountHealthItem, OverviewStats, PlatformOverviewItem, ReplyPerformancePoint, TrendPoint


def _round_metric(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 2)


def _response_minutes(posted_at: datetime, sent_at: datetime) -> Optional[float]:
    if sent_at < posted_at:
        return None
    return (sent_at - posted_at).total_seconds() / 60


def _average_response_minutes(db: Session, tenant_id: str) -> Optional[float]:
    bilibili_rows = db.execute(
        select(Comment.posted_at, ReplyAction.sent_at)
        .join(ReplyAction, ReplyAction.comment_id == Comment.id)
        .where(
            Comment.tenant_id == tenant_id,
            ReplyAction.tenant_id == tenant_id,
            ReplyAction.status == ReplyActionStatus.sent.value,
            ReplyAction.sent_at.is_not(None),
        )
    ).all()
    douyin_rows = db.execute(
        select(DouyinComment.posted_at, DouyinReplyAction.sent_at)
        .join(DouyinReplyAction, DouyinReplyAction.comment_id == DouyinComment.id)
        .where(
            DouyinComment.tenant_id == tenant_id,
            DouyinReplyAction.tenant_id == tenant_id,
            DouyinReplyAction.status == ReplyActionStatus.sent.value,
            DouyinReplyAction.sent_at.is_not(None),
        )
    ).all()
    douyin_personal_rows = db.execute(
        select(DouyinPersonalComment.posted_at, DouyinPersonalReplyAction.sent_at)
        .join(DouyinPersonalReplyAction, DouyinPersonalReplyAction.comment_id == DouyinPersonalComment.id)
        .where(
            DouyinPersonalComment.tenant_id == tenant_id,
            DouyinPersonalReplyAction.tenant_id == tenant_id,
            DouyinPersonalReplyAction.status == ReplyActionStatus.sent.value,
            DouyinPersonalReplyAction.sent_at.is_not(None),
        )
    ).all()
    rows = list(bilibili_rows) + list(douyin_rows) + list(douyin_personal_rows)
    durations = [
        duration
        for posted_at, sent_at in rows
        if posted_at and sent_at and (duration := _response_minutes(posted_at, sent_at)) is not None
    ]
    if not durations:
        return None
    return sum(durations) / len(durations)


def get_overview(db: Session, tenant_id: str) -> OverviewStats:
    bilibili_comments = db.scalar(select(func.count(Comment.id)).where(Comment.tenant_id == tenant_id)) or 0
    douyin_comments = (
        db.scalar(select(func.count(DouyinComment.id)).where(DouyinComment.tenant_id == tenant_id)) or 0
    ) + (
        db.scalar(select(func.count(DouyinPersonalComment.id)).where(DouyinPersonalComment.tenant_id == tenant_id))
        or 0
    )
    bilibili_pending_comments = (
        db.scalar(select(func.count(Comment.id)).where(Comment.tenant_id == tenant_id, Comment.is_handled.is_(False)))
        or 0
    )
    douyin_pending_comments = (
        db.scalar(
            select(func.count(DouyinComment.id)).where(
                DouyinComment.tenant_id == tenant_id, DouyinComment.is_handled.is_(False)
            )
        )
        or 0
    ) + (
        db.scalar(
            select(func.count(DouyinPersonalComment.id)).where(
                DouyinPersonalComment.tenant_id == tenant_id,
                DouyinPersonalComment.is_handled.is_(False),
            )
        )
        or 0
    )
    bilibili_replied_comments = (
        db.scalar(select(func.count(Comment.id)).where(Comment.tenant_id == tenant_id, Comment.is_replied.is_(True)))
        or 0
    )
    douyin_replied_comments = (
        db.scalar(
            select(func.count(DouyinComment.id)).where(
                DouyinComment.tenant_id == tenant_id, DouyinComment.is_replied.is_(True)
            )
        )
        or 0
    ) + (
        db.scalar(
            select(func.count(DouyinPersonalComment.id)).where(
                DouyinPersonalComment.tenant_id == tenant_id,
                DouyinPersonalComment.is_replied.is_(True),
            )
        )
        or 0
    )
    bilibili_targets = db.scalar(select(func.count(MonitorTarget.id)).where(MonitorTarget.tenant_id == tenant_id)) or 0
    douyin_targets = (
        db.scalar(select(func.count(DouyinTarget.id)).where(DouyinTarget.tenant_id == tenant_id)) or 0
    ) + (
        db.scalar(select(func.count(DouyinPersonalTarget.id)).where(DouyinPersonalTarget.tenant_id == tenant_id)) or 0
    )
    bilibili_accounts = (
        db.scalar(select(func.count(BilibiliAccount.id)).where(BilibiliAccount.tenant_id == tenant_id)) or 0
    )
    douyin_accounts = (
        db.scalar(select(func.count(DouyinAccount.id)).where(DouyinAccount.tenant_id == tenant_id)) or 0
    ) + (
        db.scalar(select(func.count(DouyinPersonalAccount.id)).where(DouyinPersonalAccount.tenant_id == tenant_id))
        or 0
    )
    failed_tasks = (
        db.scalar(
            select(func.count(TaskRun.id)).where(TaskRun.tenant_id == tenant_id, TaskRun.status == "failed")
        )
        or 0
    )
    total_comments = bilibili_comments + douyin_comments
    pending_comments = bilibili_pending_comments + douyin_pending_comments
    replied_comments = bilibili_replied_comments + douyin_replied_comments
    total_targets = bilibili_targets + douyin_targets
    total_accounts = bilibili_accounts + douyin_accounts
    reply_rate = (replied_comments / total_comments * 100) if total_comments else 0.0
    return OverviewStats(
        total_comments=total_comments,
        pending_comments=pending_comments,
        replied_comments=replied_comments,
        total_targets=total_targets,
        total_accounts=total_accounts,
        failed_tasks=failed_tasks,
        reply_rate=_round_metric(reply_rate) or 0.0,
        avg_response_minutes=_round_metric(_average_response_minutes(db, tenant_id)),
        platform_overview=[
            PlatformOverviewItem(
                platform="bilibili",
                comments=int(bilibili_comments),
                pending_comments=int(bilibili_pending_comments),
                replied_comments=int(bilibili_replied_comments),
                targets=int(bilibili_targets),
                accounts=int(bilibili_accounts),
            ),
            PlatformOverviewItem(
                platform="douyin",
                comments=int(douyin_comments),
                pending_comments=int(douyin_pending_comments),
                replied_comments=int(douyin_replied_comments),
                targets=int(douyin_targets),
                accounts=int(douyin_accounts),
            ),
        ],
    )


def get_trends(db: Session, tenant_id: str, days: int = 7) -> List[TrendPoint]:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days - 1)
    bilibili_comment_rows = db.execute(
        select(func.date(Comment.posted_at), func.count(Comment.id))
        .where(Comment.tenant_id == tenant_id, Comment.posted_at >= since)
        .group_by(func.date(Comment.posted_at))
    ).all()
    douyin_comment_rows = db.execute(
        select(func.date(DouyinComment.posted_at), func.count(DouyinComment.id))
        .where(DouyinComment.tenant_id == tenant_id, DouyinComment.posted_at >= since)
        .group_by(func.date(DouyinComment.posted_at))
    ).all()
    douyin_personal_comment_rows = db.execute(
        select(func.date(DouyinPersonalComment.posted_at), func.count(DouyinPersonalComment.id))
        .where(DouyinPersonalComment.tenant_id == tenant_id, DouyinPersonalComment.posted_at >= since)
        .group_by(func.date(DouyinPersonalComment.posted_at))
    ).all()
    bilibili_reply_rows = db.execute(
        select(func.date(ReplyAction.sent_at), func.count(ReplyAction.id))
        .where(ReplyAction.tenant_id == tenant_id, ReplyAction.sent_at.is_not(None), ReplyAction.sent_at >= since)
        .group_by(func.date(ReplyAction.sent_at))
    ).all()
    douyin_reply_rows = db.execute(
        select(func.date(DouyinReplyAction.sent_at), func.count(DouyinReplyAction.id))
        .where(
            DouyinReplyAction.tenant_id == tenant_id,
            DouyinReplyAction.sent_at.is_not(None),
            DouyinReplyAction.sent_at >= since,
        )
        .group_by(func.date(DouyinReplyAction.sent_at))
    ).all()
    douyin_personal_reply_rows = db.execute(
        select(func.date(DouyinPersonalReplyAction.sent_at), func.count(DouyinPersonalReplyAction.id))
        .where(
            DouyinPersonalReplyAction.tenant_id == tenant_id,
            DouyinPersonalReplyAction.sent_at.is_not(None),
            DouyinPersonalReplyAction.sent_at >= since,
        )
        .group_by(func.date(DouyinPersonalReplyAction.sent_at))
    ).all()
    bilibili_comment_map = {str(day): count for day, count in bilibili_comment_rows}
    douyin_comment_map = {str(day): count for day, count in douyin_comment_rows}
    for day, count in douyin_personal_comment_rows:
        douyin_comment_map[str(day)] = int(douyin_comment_map.get(str(day), 0)) + int(count)
    bilibili_reply_map = {str(day): count for day, count in bilibili_reply_rows}
    douyin_reply_map = {str(day): count for day, count in douyin_reply_rows}
    for day, count in douyin_personal_reply_rows:
        douyin_reply_map[str(day)] = int(douyin_reply_map.get(str(day), 0)) + int(count)
    items: List[TrendPoint] = []
    for idx in range(days):
        day = (since + timedelta(days=idx)).date().isoformat()
        bilibili_comments = int(bilibili_comment_map.get(day, 0))
        douyin_comments = int(douyin_comment_map.get(day, 0))
        bilibili_replies = int(bilibili_reply_map.get(day, 0))
        douyin_replies = int(douyin_reply_map.get(day, 0))
        items.append(
            TrendPoint(
                day=day,
                comments=bilibili_comments + douyin_comments,
                replies=bilibili_replies + douyin_replies,
                bilibili_comments=bilibili_comments,
                douyin_comments=douyin_comments,
                bilibili_replies=bilibili_replies,
                douyin_replies=douyin_replies,
            )
        )
    return items


def get_account_health(db: Session, tenant_id: str) -> List[AccountHealthItem]:
    items = []
    bilibili_accounts = db.scalars(select(BilibiliAccount).where(BilibiliAccount.tenant_id == tenant_id)).all()
    for account in bilibili_accounts:
        pending = (
            db.scalar(
                select(func.count(Comment.id)).where(
                    Comment.tenant_id == tenant_id,
                    Comment.account_id == account.id,
                    Comment.is_handled.is_(False),
                )
            )
            or 0
        )
        items.append(
            AccountHealthItem(
                platform="bilibili",
                account_id=account.id,
                username=account.username,
                status=account.status,
                risk_status=account.risk_status,
                last_error=account.last_error,
                pending_comments=int(pending),
            )
        )
    douyin_accounts = db.scalars(select(DouyinAccount).where(DouyinAccount.tenant_id == tenant_id)).all()
    for account in douyin_accounts:
        pending = (
            db.scalar(
                select(func.count(DouyinComment.id)).where(
                    DouyinComment.tenant_id == tenant_id,
                    DouyinComment.account_id == account.id,
                    DouyinComment.is_handled.is_(False),
                )
            )
            or 0
        )
        items.append(
            AccountHealthItem(
                platform="douyin",
                account_id=account.id,
                username=account.nickname,
                status=account.status,
                risk_status=None,
                last_error=account.last_error,
                pending_comments=int(pending),
            )
        )
    douyin_personal_accounts = db.scalars(
        select(DouyinPersonalAccount).where(DouyinPersonalAccount.tenant_id == tenant_id)
    ).all()
    for account in douyin_personal_accounts:
        pending = (
            db.scalar(
                select(func.count(DouyinPersonalComment.id)).where(
                    DouyinPersonalComment.tenant_id == tenant_id,
                    DouyinPersonalComment.account_id == account.id,
                    DouyinPersonalComment.is_handled.is_(False),
                )
            )
            or 0
        )
        items.append(
            AccountHealthItem(
                platform="douyin",
                account_id=account.id,
                username=f"{account.nickname} [personal]",
                status=account.status,
                risk_status=None,
                last_error=account.last_error,
                pending_comments=int(pending),
            )
        )
    return items


def get_reply_performance(db: Session, tenant_id: str, days: int = 7) -> List[ReplyPerformancePoint]:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days - 1)
    bilibili_rows = db.execute(
        select(ReplyAction, Comment.posted_at)
        .join(Comment, Comment.id == ReplyAction.comment_id)
        .where(
            ReplyAction.tenant_id == tenant_id,
            or_(ReplyAction.created_at >= since, ReplyAction.sent_at >= since),
        )
    ).all()
    douyin_rows = db.execute(
        select(DouyinReplyAction, DouyinComment.posted_at)
        .join(DouyinComment, DouyinComment.id == DouyinReplyAction.comment_id)
        .where(
            DouyinReplyAction.tenant_id == tenant_id,
            or_(DouyinReplyAction.created_at >= since, DouyinReplyAction.sent_at >= since),
        )
    ).all()
    douyin_personal_rows = db.execute(
        select(DouyinPersonalReplyAction, DouyinPersonalComment.posted_at)
        .join(DouyinPersonalComment, DouyinPersonalComment.id == DouyinPersonalReplyAction.comment_id)
        .where(
            DouyinPersonalReplyAction.tenant_id == tenant_id,
            or_(DouyinPersonalReplyAction.created_at >= since, DouyinPersonalReplyAction.sent_at >= since),
        )
    ).all()

    daily: DefaultDict[str, Dict[str, object]] = defaultdict(
        lambda: {
            "sent": 0,
            "failed": 0,
            "durations": [],
            "bilibili_sent": 0,
            "douyin_sent": 0,
            "bilibili_failed": 0,
            "douyin_failed": 0,
        }
    )

    for action, posted_at in bilibili_rows:
        if action.status == ReplyActionStatus.sent.value and action.sent_at is not None:
            day = action.sent_at.astimezone(timezone.utc).date().isoformat()
            if day < since.date().isoformat():
                continue
            daily[day]["sent"] = int(daily[day]["sent"]) + 1
            daily[day]["bilibili_sent"] = int(daily[day]["bilibili_sent"]) + 1
            if posted_at is not None:
                duration = _response_minutes(posted_at, action.sent_at)
                if duration is not None:
                    durations = daily[day]["durations"]
                    assert isinstance(durations, list)
                    durations.append(duration)
        elif action.status == ReplyActionStatus.failed.value:
            day = action.created_at.astimezone(timezone.utc).date().isoformat()
            if day < since.date().isoformat():
                continue
            daily[day]["failed"] = int(daily[day]["failed"]) + 1
            daily[day]["bilibili_failed"] = int(daily[day]["bilibili_failed"]) + 1

    for action, posted_at in douyin_rows:
        if action.status == ReplyActionStatus.sent.value and action.sent_at is not None:
            day = action.sent_at.astimezone(timezone.utc).date().isoformat()
            if day < since.date().isoformat():
                continue
            daily[day]["sent"] = int(daily[day]["sent"]) + 1
            daily[day]["douyin_sent"] = int(daily[day]["douyin_sent"]) + 1
            if posted_at is not None:
                duration = _response_minutes(posted_at, action.sent_at)
                if duration is not None:
                    durations = daily[day]["durations"]
                    assert isinstance(durations, list)
                    durations.append(duration)
        elif action.status == ReplyActionStatus.failed.value:
            day = action.created_at.astimezone(timezone.utc).date().isoformat()
            if day < since.date().isoformat():
                continue
            daily[day]["failed"] = int(daily[day]["failed"]) + 1
            daily[day]["douyin_failed"] = int(daily[day]["douyin_failed"]) + 1
    for action, posted_at in douyin_personal_rows:
        if action.status == ReplyActionStatus.sent.value and action.sent_at is not None:
            day = action.sent_at.astimezone(timezone.utc).date().isoformat()
            if day < since.date().isoformat():
                continue
            daily[day]["sent"] = int(daily[day]["sent"]) + 1
            daily[day]["douyin_sent"] = int(daily[day]["douyin_sent"]) + 1
            if posted_at is not None:
                duration = _response_minutes(posted_at, action.sent_at)
                if duration is not None:
                    durations = daily[day]["durations"]
                    assert isinstance(durations, list)
                    durations.append(duration)
        elif action.status == ReplyActionStatus.failed.value:
            day = action.created_at.astimezone(timezone.utc).date().isoformat()
            if day < since.date().isoformat():
                continue
            daily[day]["failed"] = int(daily[day]["failed"]) + 1
            daily[day]["douyin_failed"] = int(daily[day]["douyin_failed"]) + 1

    items: List[ReplyPerformancePoint] = []
    for idx in range(days):
        day = (since + timedelta(days=idx)).date().isoformat()
        durations = daily[day]["durations"]
        assert isinstance(durations, list)
        avg_response_minutes = sum(durations) / len(durations) if durations else None
        items.append(
            ReplyPerformancePoint(
                day=day,
                sent=int(daily[day]["sent"]),
                failed=int(daily[day]["failed"]),
                avg_response_minutes=_round_metric(avg_response_minutes),
                bilibili_sent=int(daily[day]["bilibili_sent"]),
                douyin_sent=int(daily[day]["douyin_sent"]),
                bilibili_failed=int(daily[day]["bilibili_failed"]),
                douyin_failed=int(daily[day]["douyin_failed"]),
            )
        )
    return items
