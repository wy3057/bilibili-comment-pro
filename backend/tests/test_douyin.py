from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.models.entities import DouyinComment, ReplyActionStatus, Tenant, User
from app.schemas.douyin import DouyinAccountImport, DouyinAppCreate, DouyinTargetCreate
from app.services import douyin as douyin_service


def _seed_tenant_user(db_session):
    tenant = Tenant(name="Tenant Douyin", slug="tenant-douyin", is_active=True)
    user = User(email="douyin@example.com", display_name="Douyin User", password_hash="hash", is_active=True)
    db_session.add_all([tenant, user])
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(user)
    return tenant, user


async def test_douyin_crud_poll_and_reply_flow(db_session, monkeypatch):
    tenant, user = _seed_tenant_user(db_session)

    app = douyin_service.create_app(
        db_session,
        tenant.id,
        DouyinAppCreate(name="Douyin Mini App", client_key="client-key", client_secret="client-secret"),
        user,
    )
    assert app.client_key == "client-key"

    account = await douyin_service.import_account(
        db_session,
        tenant.id,
        DouyinAccountImport(
            app_id=app.id,
            open_id="open-id-1",
            access_token="act.mock",
            nickname="Tester",
            access_token_expires_at=datetime.now(timezone.utc),
        ),
        user,
    )
    assert account.nickname == "Tester"

    target = douyin_service.create_target(
        db_session,
        tenant.id,
        DouyinTargetCreate(account_id=account.id, item_id="item-1", title="Test Item", poll_interval=300),
        user,
    )
    assert target.item_id == "item-1"

    async def fake_request(method, path, access_token, *, params=None, json_body=None):
        if path.endswith("/list_comment/"):
            return {
                "comments": [
                    {
                        "comment_id": "comment-1",
                        "content": "hello douyin",
                        "create_time": int(datetime.now(timezone.utc).timestamp()),
                        "digg_count": 3,
                        "reply_comment_total": 0,
                        "comment_user_open_id": "viewer-1",
                        "comment_user_nickname": "Viewer",
                    }
                ],
                "has_more": False,
                "cursor": 0,
            }
        if path.endswith("/list_comment_reply/"):
            return {"comments": [], "has_more": False, "cursor": 0}
        if path.endswith("/reply_comment/"):
            return {"error_code": 0, "description": "ok"}
        raise AssertionError(path)

    monkeypatch.setattr(douyin_service.gateway, "_request", fake_request)

    poll_result = await douyin_service.gateway.poll_target_comments(db_session, target)
    assert poll_result["created"] == 1

    comment = db_session.query(DouyinComment).filter_by(target_id=target.id, comment_id="comment-1").one()
    assert comment.content == "hello douyin"
    assert comment.is_replied is False

    action = await douyin_service.gateway.reply_to_comment(
        db_session,
        tenant_id=tenant.id,
        account_id=account.id,
        comment_id=comment.id,
        content="reply from ops",
        user=user,
    )

    db_session.refresh(comment)

    assert action.status == ReplyActionStatus.sent.value
    assert comment.is_replied is True
    assert comment.is_handled is True


async def test_douyin_refresh_account_updates_tokens(db_session, monkeypatch):
    tenant, user = _seed_tenant_user(db_session)
    app = douyin_service.create_app(
        db_session,
        tenant.id,
        DouyinAppCreate(name="Douyin Mini App", client_key="client-key", client_secret="client-secret"),
        user,
    )
    account = await douyin_service.import_account(
        db_session,
        tenant.id,
        DouyinAccountImport(
            app_id=app.id,
            open_id="open-id-2",
            access_token="old-access",
            refresh_token="old-refresh",
            nickname="Refresh Tester",
        ),
        user,
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 7200,
                }
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, data=None, headers=None):
            assert url.endswith("/oauth/refresh_token/")
            assert data["client_key"] == "client-key"
            assert data["refresh_token"] == "old-refresh"
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    refreshed = await douyin_service.gateway.refresh_account(db_session, account)

    assert douyin_service.gateway.load_access_token(refreshed) == "new-access"
    assert douyin_service.gateway.load_refresh_token(refreshed) == "new-refresh"
    assert refreshed.status == "active"
    assert refreshed.access_token_expires_at is not None
