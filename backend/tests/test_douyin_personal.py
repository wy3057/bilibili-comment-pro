from __future__ import annotations

from datetime import datetime, timezone

from app.models.entities import DouyinPersonalComment, ReplyActionStatus, Tenant, User
from app.schemas.douyin import DouyinPersonalCookieImport, DouyinPersonalTargetCreate
from app.services import douyin_personal as douyin_personal_service


def _seed_tenant_user(db_session):
    tenant = Tenant(name="Tenant Douyin Personal", slug="tenant-douyin-personal", is_active=True)
    user = User(email="douyin-personal@example.com", display_name="Douyin Personal User", password_hash="hash", is_active=True)
    db_session.add_all([tenant, user])
    db_session.commit()
    db_session.refresh(tenant)
    db_session.refresh(user)
    return tenant, user


async def test_douyin_personal_import_target_poll_and_reply_flow(db_session, monkeypatch):
    tenant, user = _seed_tenant_user(db_session)

    async def fake_normalize(cookie: str):
        assert "sessionid_ss=abc" in cookie
        return {
            "cookie": cookie,
            "runtime": {"msToken": "ms", "s_v_web_id": "verify", "ttwid": "ttwid"},
            "profile": {"external_user_id": "personal-user-1", "nickname": "Personal Tester", "avatar_url": "https://example.com/avatar.png"},
        }

    async def fake_resolve_target(**kwargs):
        assert kwargs["video_url"] == "https://www.douyin.com/video/1234567890"
        return {
            "aweme_id": "1234567890",
            "title": "Personal Video",
            "video_url": "https://www.douyin.com/video/1234567890",
        }

    async def fake_fetch_comments(**kwargs):
        assert kwargs["aweme_id"] == "1234567890"
        return {
            "comments": [
                {
                    "comment_id": "pc-1",
                    "content": "hello personal douyin",
                    "create_time": int(datetime.now(timezone.utc).timestamp()),
                    "digg_count": 5,
                    "reply_comment_total": 0,
                    "comment_user_nickname": "Viewer",
                    "user_id": "viewer-1",
                }
            ]
        }

    async def fake_reply_comment(**kwargs):
        assert kwargs["aweme_id"] == "1234567890"
        assert kwargs["comment_id"] == "pc-1"
        assert kwargs["content"] == "reply from personal ops"
        return {"ok": True, "description": "sent"}

    monkeypatch.setattr(douyin_personal_service.helper_client, "normalize_cookie", fake_normalize)
    monkeypatch.setattr(douyin_personal_service.helper_client, "resolve_target", fake_resolve_target)
    monkeypatch.setattr(douyin_personal_service.helper_client, "fetch_comments", fake_fetch_comments)
    monkeypatch.setattr(douyin_personal_service.helper_client, "reply_comment", fake_reply_comment)

    account = await douyin_personal_service.import_cookie_account(
        db_session,
        tenant.id,
        DouyinPersonalCookieImport(cookie="sessionid_ss=abc; uid_tt=uid"),
        user,
    )
    assert account.nickname == "Personal Tester"

    target = await douyin_personal_service.create_target(
        db_session,
        tenant.id,
        DouyinPersonalTargetCreate(
            account_id=account.id,
            video_url="https://www.douyin.com/video/1234567890",
            poll_interval=300,
        ),
        user,
    )
    assert target.aweme_id == "1234567890"

    poll_result = await douyin_personal_service.gateway.poll_target_comments(db_session, target)
    assert poll_result["created"] == 1

    comment = (
        db_session.query(DouyinPersonalComment)
        .filter_by(target_id=target.id, comment_id="pc-1")
        .one()
    )
    assert comment.content == "hello personal douyin"
    assert comment.is_replied is False

    action = await douyin_personal_service.gateway.reply_to_comment(
        db_session,
        tenant_id=tenant.id,
        account_id=account.id,
        comment_id=comment.id,
        content="reply from personal ops",
        user=user,
    )

    db_session.refresh(comment)

    assert action.status == ReplyActionStatus.sent.value
    assert comment.is_replied is True
    assert comment.is_handled is True
