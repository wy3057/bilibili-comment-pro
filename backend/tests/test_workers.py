from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.workers.tasks import (
    should_poll_target,
    should_refresh_douyin_account,
    should_refresh_douyin_personal_account,
)


def test_should_poll_target_when_never_polled() -> None:
    target = SimpleNamespace(status="active", last_polled_at=None, poll_interval=300)
    assert should_poll_target(target) is True


def test_should_not_poll_target_before_interval() -> None:
    now = datetime.now(timezone.utc)
    target = SimpleNamespace(
        status="active",
        last_polled_at=now - timedelta(seconds=120),
        poll_interval=300,
    )
    assert should_poll_target(target, now=now) is False


def test_should_poll_target_after_interval() -> None:
    now = datetime.now(timezone.utc)
    target = SimpleNamespace(
        status="active",
        last_polled_at=now - timedelta(seconds=301),
        poll_interval=300,
    )
    assert should_poll_target(target, now=now) is True


def test_should_not_poll_non_active_target() -> None:
    target = SimpleNamespace(status="paused", last_polled_at=None, poll_interval=300)
    assert should_poll_target(target) is False


def test_should_refresh_douyin_account_when_not_active() -> None:
    account = SimpleNamespace(status="expired", access_token_expires_at=None)
    assert should_refresh_douyin_account(account) is True


def test_should_refresh_douyin_account_near_expiry() -> None:
    now = datetime.now(timezone.utc)
    account = SimpleNamespace(status="active", access_token_expires_at=now + timedelta(hours=6))
    assert should_refresh_douyin_account(account, now=now) is True


def test_should_not_refresh_douyin_account_when_token_is_fresh() -> None:
    now = datetime.now(timezone.utc)
    account = SimpleNamespace(status="active", access_token_expires_at=now + timedelta(days=2))
    assert should_refresh_douyin_account(account, now=now) is False


def test_should_refresh_douyin_personal_account_when_not_active() -> None:
    account = SimpleNamespace(status="expired", last_validated_at=None)
    assert should_refresh_douyin_personal_account(account) is True


def test_should_refresh_douyin_personal_account_when_validation_is_stale() -> None:
    now = datetime.now(timezone.utc)
    account = SimpleNamespace(status="active", last_validated_at=now - timedelta(hours=13))
    assert should_refresh_douyin_personal_account(account, now=now) is True


def test_should_not_refresh_douyin_personal_account_when_recently_validated() -> None:
    now = datetime.now(timezone.utc)
    account = SimpleNamespace(status="active", last_validated_at=now - timedelta(hours=2))
    assert should_refresh_douyin_personal_account(account, now=now) is False
