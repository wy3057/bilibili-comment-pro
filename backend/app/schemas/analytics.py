from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PlatformOverviewItem(BaseModel):
    platform: str
    comments: int
    pending_comments: int
    replied_comments: int
    targets: int
    accounts: int


class OverviewStats(BaseModel):
    total_comments: int
    pending_comments: int
    replied_comments: int
    total_targets: int
    total_accounts: int
    failed_tasks: int
    reply_rate: float
    avg_response_minutes: Optional[float] = None
    platform_overview: list[PlatformOverviewItem]


class TrendPoint(BaseModel):
    day: str
    comments: int
    replies: int
    bilibili_comments: int = 0
    douyin_comments: int = 0
    bilibili_replies: int = 0
    douyin_replies: int = 0


class ReplyPerformancePoint(BaseModel):
    day: str
    sent: int
    failed: int
    avg_response_minutes: Optional[float] = None
    bilibili_sent: int = 0
    douyin_sent: int = 0
    bilibili_failed: int = 0
    douyin_failed: int = 0


class AccountHealthItem(BaseModel):
    platform: str
    account_id: str
    username: str
    status: str
    risk_status: Optional[str] = None
    last_error: Optional[str] = None
    pending_comments: int
