from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_healthz_and_bootstrap_login_smoke(tmp_path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "smoke.db"
    env = os.environ.copy()
    env["APP_ENV"] = "test"
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"

    script = """
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.entities import AccountStatus, BilibiliAccount, Comment, MonitorTarget, RiskStatus
from app.services.bilibili_gateway import gateway

async def fake_send_reply(db, action, account_obj, comment_row, content):
    action.status = "sent"
    action.response_payload = {"ok": True}
    comment_row.is_replied = True
    comment_row.is_handled = True
    db.add(action)
    db.add(comment_row)
    db.commit()
    db.refresh(action)
    return action

async def fake_import_video_targets(_account):
    return [
        {"oid": 123456, "bvid": "BV1Smoke1111", "title": "Smoke Target", "owner_mid": 7},
        {"oid": 223344, "bvid": "BV1Smoke2222", "title": "Imported Target", "owner_mid": 8},
    ]

gateway.send_reply = fake_send_reply
gateway.import_video_targets = fake_import_video_targets

with TestClient(app) as client:
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    login = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "ChangeMe123!"},
    )
    assert login.status_code == 200
    body = login.json()
    assert "access_token" in body
    assert "refresh_token" in body

    refresh = client.post(
        "/api/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert refresh.status_code == 200
    refreshed = refresh.json()
    assert refreshed["access_token"] != body["access_token"]
    assert refreshed["refresh_token"] != body["refresh_token"]

    logout = client.post(
        "/api/auth/logout",
        json={"refresh_token": refreshed["refresh_token"]},
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert logout.status_code == 200

    relogin = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "ChangeMe123!"},
    )
    relogin_body = relogin.json()
    headers = {"Authorization": f"Bearer {relogin_body['access_token']}"}
    create_tenant = client.post(
        "/api/tenants",
        json={
            "name": "Second Tenant",
            "slug": "second-tenant",
            "description": "smoke tenant",
        },
        headers=headers,
    )
    assert create_tenant.status_code == 200
    tenant = create_tenant.json()
    assert tenant["slug"] == "second-tenant"

    tenants = client.get("/api/tenants", headers=headers)
    assert tenants.status_code == 200
    assert len(tenants.json()) >= 2

    create_webhook = client.post(
        "/api/notifications/webhooks",
        json={
            "name": "smoke",
            "provider": "dingtalk",
            "webhook_url": "https://example.com/webhook",
            "is_enabled": True,
        },
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert create_webhook.status_code == 200
    webhook = create_webhook.json()
    assert webhook["name"] == "smoke"

    list_webhooks = client.get("/api/notifications/webhooks", headers={**headers, "X-Tenant-Id": tenant["id"]})
    assert list_webhooks.status_code == 200
    assert len(list_webhooks.json()) == 1

    db = SessionLocal()
    account = BilibiliAccount(
        tenant_id=tenant["id"],
        uid=10086,
        username="smoke-account",
        status=AccountStatus.active.value,
        risk_status=RiskStatus.normal.value,
    )
    db.add(account)
    db.flush()
    target = MonitorTarget(
        tenant_id=tenant["id"],
        account_id=account.id,
        oid=123456,
        bvid="BV1Smoke1111",
        title="Smoke Target",
        poll_interval=300,
        status="active",
    )
    db.add(target)
    db.flush()
    comment = Comment(
        tenant_id=tenant["id"],
        target_id=target.id,
        account_id=account.id,
        rpid=7001,
        root_rpid=7001,
        parent_rpid=None,
        oid=123456,
        member_mid=42,
        member_name="Smoke User",
        message="please reply",
        posted_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        like_count=0,
        is_top_level=True,
        raw_payload={"source": "smoke"},
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    preview = client.get(
        f"/api/targets/import-preview/{account.id}",
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert preview.status_code == 200
    preview_rows = preview.json()
    assert len(preview_rows) == 2
    assert any(row["bvid"] == "BV1Smoke1111" and row["already_monitored"] for row in preview_rows)
    assert any(row["bvid"] == "BV1Smoke2222" and not row["already_monitored"] for row in preview_rows)

    imported = client.post(
        f"/api/targets/import-from-account/{account.id}",
        json={
            "only_missing": False,
            "selected_bvids": ["BV1Smoke1111", "BV1Smoke2222"],
            "poll_interval": 600,
        },
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert imported.status_code == 200
    imported_rows = imported.json()
    assert len(imported_rows) == 1
    assert imported_rows[0]["bvid"] == "BV1Smoke2222"
    assert imported_rows[0]["poll_interval"] == 600

    handled = client.patch(
        "/api/comments/handled",
        json={"comment_ids": [comment.id], "is_handled": True},
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert handled.status_code == 200

    draft = client.post(
        "/api/reply-drafts",
        json={"comment_id": comment.id, "content": "draft from smoke"},
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert draft.status_code == 200
    draft_body = draft.json()

    reply = client.post(
        "/api/reply-actions/send",
        json={"comment_id": comment.id, "account_id": account.id, "draft_id": draft_body["id"]},
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert reply.status_code == 200
    assert reply.json()["status"] == "sent"

    detail = client.get(
        f"/api/comments/{comment.id}",
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["id"] == comment.id
    assert len(detail_body["reply_drafts"]) == 1
    assert len(detail_body["reply_actions"]) == 1
    assert detail_body["reply_actions"][0]["status"] == "sent"

    ops_comments = client.get(
        "/api/ops/comments",
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert ops_comments.status_code == 200
    ops_comment_rows = ops_comments.json()
    assert len(ops_comment_rows) == 1
    assert ops_comment_rows[0]["platform"] == "bilibili"

    ops_detail = client.get(
        f"/api/ops/comments/bilibili/{comment.id}",
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert ops_detail.status_code == 200
    assert ops_detail.json()["platform"] == "bilibili"

    ops_replies = client.get(
        "/api/ops/reply-actions",
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert ops_replies.status_code == 200
    assert len(ops_replies.json()) == 1
    assert ops_replies.json()[0]["platform"] == "bilibili"

    audits = client.get(
        "/api/audit-logs",
        headers={**headers, "X-Tenant-Id": tenant["id"]},
    )
    assert audits.status_code == 200
    audit_rows = audits.json()
    actions = {row["action"] for row in audit_rows}
    assert "comment.handle.update" in actions
    assert "reply.draft.create" in actions
    assert "reply.send.requested" in actions
    assert "reply.send.completed" in actions
    assert all("created_at" in row for row in audit_rows)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
