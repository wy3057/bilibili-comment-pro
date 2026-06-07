from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery("bilibili_comment_platform", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {
    "poll-active-targets": {
        "task": "app.workers.tasks.poll_active_targets",
        "schedule": 60.0,
    },
    "refresh-active-accounts": {
        "task": "app.workers.tasks.refresh_accounts",
        "schedule": 900.0,
    },
}
celery_app.conf.timezone = "Asia/Shanghai"

