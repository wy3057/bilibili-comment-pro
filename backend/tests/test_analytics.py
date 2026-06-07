from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.entities import (
    AccountStatus,
    BilibiliAccount,
    Comment,
    DouyinAccount,
    DouyinApp,
    DouyinComment,
    DouyinReplyAction,
    DouyinTarget,
    MonitorTarget,
    ReplyAction,
    ReplyActionStatus,
    RiskStatus,
    TaskKind,
    TaskRun,
    TaskStatus,
    Tenant,
)
from app.services import analytics as analytics_service
from app.services import system as system_service


def _seed_analytics_context(db_session):
    now = datetime.now(timezone.utc)
    tenant = Tenant(name="Tenant Analytics", slug="tenant-analytics", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    account = BilibiliAccount(
        tenant_id=tenant.id,
        uid=50001,
        username="analytics-account",
        status=AccountStatus.active.value,
        risk_status=RiskStatus.normal.value,
    )
    db_session.add(account)
    db_session.flush()

    target = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=987654,
        bvid="BV1analytics1",
        title="Analytics Target",
        poll_interval=300,
        status="active",
    )
    db_session.add(target)
    db_session.flush()

    replied_comment = Comment(
        tenant_id=tenant.id,
        target_id=target.id,
        account_id=account.id,
        rpid=9101,
        root_rpid=9101,
        parent_rpid=None,
        oid=target.oid,
        member_mid=101,
        member_name="Alice",
        message="First comment",
        posted_at=now - timedelta(minutes=90),
        like_count=2,
        is_top_level=True,
        is_handled=True,
        is_replied=True,
        raw_payload={"source": "analytics"},
    )
    pending_comment = Comment(
        tenant_id=tenant.id,
        target_id=target.id,
        account_id=account.id,
        rpid=9102,
        root_rpid=9102,
        parent_rpid=None,
        oid=target.oid,
        member_mid=102,
        member_name="Bob",
        message="Second comment",
        posted_at=now - timedelta(minutes=30),
        like_count=0,
        is_top_level=True,
        is_handled=False,
        is_replied=False,
        raw_payload={"source": "analytics"},
    )
    old_comment = Comment(
        tenant_id=tenant.id,
        target_id=target.id,
        account_id=account.id,
        rpid=9103,
        root_rpid=9103,
        parent_rpid=None,
        oid=target.oid,
        member_mid=103,
        member_name="Carol",
        message="Third comment",
        posted_at=now - timedelta(days=2),
        like_count=1,
        is_top_level=True,
        is_handled=True,
        is_replied=False,
        raw_payload={"source": "analytics"},
    )
    db_session.add_all([replied_comment, pending_comment, old_comment])
    db_session.flush()

    sent_action = ReplyAction(
        tenant_id=tenant.id,
        account_id=account.id,
        comment_id=replied_comment.id,
        operator_id=None,
        request_payload={"content": "Reply sent"},
        response_payload={"ok": True},
        status=ReplyActionStatus.sent.value,
        sent_at=now - timedelta(minutes=30),
        created_at=now - timedelta(minutes=40),
        updated_at=now - timedelta(minutes=30),
    )
    failed_recent_action = ReplyAction(
        tenant_id=tenant.id,
        account_id=account.id,
        comment_id=pending_comment.id,
        operator_id=None,
        request_payload={"content": "Reply failed"},
        response_payload=None,
        status=ReplyActionStatus.failed.value,
        error_message="rate limited",
        sent_at=None,
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add_all([sent_action, failed_recent_action])

    douyin_app = DouyinApp(
        tenant_id=tenant.id,
        name="Douyin App",
        client_key="douyin-client-key",
        encrypted_client_secret="encrypted",
        is_active=True,
    )
    db_session.add(douyin_app)
    db_session.flush()

    douyin_account = DouyinAccount(
        tenant_id=tenant.id,
        app_id=douyin_app.id,
        open_id="douyin-open-id",
        nickname="Douyin Operator",
        encrypted_access_token="encrypted-access",
        encrypted_refresh_token=None,
        status=AccountStatus.active.value,
        last_validated_at=now,
        last_error=None,
    )
    db_session.add(douyin_account)
    db_session.flush()

    douyin_target = DouyinTarget(
        tenant_id=tenant.id,
        account_id=douyin_account.id,
        item_id="douyin-item-1",
        title="Douyin Item",
        poll_interval=300,
        status="active",
    )
    db_session.add(douyin_target)
    db_session.flush()

    douyin_replied_comment = DouyinComment(
        tenant_id=tenant.id,
        target_id=douyin_target.id,
        account_id=douyin_account.id,
        comment_id="dy-comment-1",
        parent_comment_id=None,
        user_open_id="viewer-1",
        user_nickname="Viewer A",
        content="Douyin replied comment",
        posted_at=now - timedelta(minutes=45),
        digg_count=4,
        reply_count=0,
        is_top_level=True,
        is_handled=True,
        is_replied=True,
        raw_payload={"source": "analytics"},
    )
    douyin_pending_comment = DouyinComment(
        tenant_id=tenant.id,
        target_id=douyin_target.id,
        account_id=douyin_account.id,
        comment_id="dy-comment-2",
        parent_comment_id=None,
        user_open_id="viewer-2",
        user_nickname="Viewer B",
        content="Douyin pending comment",
        posted_at=now - timedelta(minutes=20),
        digg_count=1,
        reply_count=0,
        is_top_level=True,
        is_handled=False,
        is_replied=False,
        raw_payload={"source": "analytics"},
    )
    db_session.add_all([douyin_replied_comment, douyin_pending_comment])
    db_session.flush()

    douyin_sent_action = DouyinReplyAction(
        tenant_id=tenant.id,
        account_id=douyin_account.id,
        comment_id=douyin_replied_comment.id,
        operator_id=None,
        content="Douyin reply sent",
        response_payload={"ok": True},
        status=ReplyActionStatus.sent.value,
        sent_at=now - timedelta(minutes=15),
        created_at=now - timedelta(minutes=16),
        updated_at=now - timedelta(minutes=15),
    )
    douyin_failed_action = DouyinReplyAction(
        tenant_id=tenant.id,
        account_id=douyin_account.id,
        comment_id=douyin_pending_comment.id,
        operator_id=None,
        content="Douyin reply failed",
        response_payload=None,
        status=ReplyActionStatus.failed.value,
        error_message="permission denied",
        sent_at=None,
        created_at=now - timedelta(minutes=5),
        updated_at=now - timedelta(minutes=5),
    )
    db_session.add_all([douyin_sent_action, douyin_failed_action])

    recent_failed_task = TaskRun(
        tenant_id=tenant.id,
        account_id=account.id,
        target_id=target.id,
        task_name="poll_target_comments",
        task_kind=TaskKind.poll_comments.value,
        status=TaskStatus.failed.value,
        started_at=now - timedelta(hours=2, minutes=5),
        finished_at=now - timedelta(hours=2),
        duration_ms=300000,
        detail={},
        error_message="network error",
    )
    old_failed_task = TaskRun(
        tenant_id=tenant.id,
        account_id=account.id,
        target_id=target.id,
        task_name="refresh_credentials",
        task_kind=TaskKind.refresh_credentials.value,
        status=TaskStatus.failed.value,
        started_at=now - timedelta(days=2, minutes=5),
        finished_at=now - timedelta(days=2),
        duration_ms=300000,
        detail={},
        error_message="expired",
    )
    running_task = TaskRun(
        tenant_id=tenant.id,
        account_id=account.id,
        target_id=target.id,
        task_name="sync_targets",
        task_kind=TaskKind.sync_targets.value,
        status=TaskStatus.running.value,
        started_at=now - timedelta(minutes=5),
        finished_at=None,
        duration_ms=None,
        detail={},
        error_message=None,
    )
    db_session.add_all([recent_failed_task, old_failed_task, running_task])
    db_session.commit()
    return tenant


def test_overview_exposes_reply_rate_and_avg_response_minutes(db_session):
    tenant = _seed_analytics_context(db_session)

    overview = analytics_service.get_overview(db_session, tenant.id)

    assert overview.total_comments == 5
    assert overview.pending_comments == 2
    assert overview.replied_comments == 2
    assert overview.total_targets == 2
    assert overview.total_accounts == 2
    assert overview.failed_tasks == 2
    assert overview.reply_rate == 40.0
    assert overview.avg_response_minutes == 45.0
    assert {item.platform for item in overview.platform_overview} == {"bilibili", "douyin"}


def test_comment_trends_include_bilibili_and_douyin_breakdown(db_session):
    tenant = _seed_analytics_context(db_session)
    today = datetime.now(timezone.utc).date().isoformat()

    points = analytics_service.get_trends(db_session, tenant.id, days=3)
    today_point = next(point for point in points if point.day == today)

    assert today_point.comments == 4
    assert today_point.bilibili_comments == 2
    assert today_point.douyin_comments == 2
    assert today_point.replies == 2
    assert today_point.bilibili_replies == 1
    assert today_point.douyin_replies == 1


def test_reply_performance_groups_sent_failed_and_response_time(db_session):
    tenant = _seed_analytics_context(db_session)

    points = analytics_service.get_reply_performance(db_session, tenant.id, days=3)
    data_point = next(point for point in points if point.sent > 0 or point.failed > 0)

    assert data_point.sent == 2
    assert data_point.failed == 2
    assert data_point.bilibili_sent == 1
    assert data_point.douyin_sent == 1
    assert data_point.bilibili_failed == 1
    assert data_point.douyin_failed == 1
    assert data_point.avg_response_minutes == 45.0


def test_system_metrics_only_count_failures_within_last_24_hours(db_session):
    tenant = _seed_analytics_context(db_session)

    metrics = system_service.get_metrics_summary(db_session, tenant.id)

    assert metrics.queue_backlog == 1
    assert metrics.failed_tasks_last_24h == 1
    assert metrics.login_expired_accounts == 0
    assert metrics.active_targets == 2
    assert metrics.risk_accounts == 0
