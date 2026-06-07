from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_payload, encrypt_payload
from app.core.metrics import COMMENTS_DISCOVERED_TOTAL, REPLY_ACTIONS_TOTAL, TARGET_POLLS_TOTAL
from app.models.entities import (
    AccountStatus,
    DouyinAccount,
    DouyinApp,
    DouyinComment,
    DouyinOAuthSession,
    DouyinReplyAction,
    DouyinTarget,
    ReplyActionStatus,
    User,
)
from app.schemas.douyin import DouyinAccountImport, DouyinAppCreate, DouyinTargetCreate
from app.services.audit import log_audit
from app.services.notifications import notify_new_comments
from app.services.realtime import manager as websocket_manager
from app.services.task_runs import finish_task_run, start_task_run

DOUYIN_API_BASE = "https://open.douyin.com"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _expires_at(seconds: Any) -> Optional[datetime]:
    if seconds in (None, ""):
        return None
    try:
        ttl = int(seconds)
    except (TypeError, ValueError):
        return None
    return _utcnow() + timedelta(seconds=ttl)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    if isinstance(value, str) and value.isdigit():
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    return _utcnow()


def _extract_error_message(payload: dict) -> str:
    return (
        payload.get("description")
        or payload.get("message")
        or payload.get("err_tips")
        or payload.get("msg")
        or "Douyin API request failed"
    )


def list_apps(db: Session, tenant_id: str) -> List[DouyinApp]:
    stmt: Select = select(DouyinApp).where(DouyinApp.tenant_id == tenant_id).order_by(DouyinApp.created_at.desc())
    return list(db.scalars(stmt).all())


def create_app(db: Session, tenant_id: str, payload: DouyinAppCreate, user: User) -> DouyinApp:
    existing = db.scalar(
        select(DouyinApp).where(DouyinApp.tenant_id == tenant_id, DouyinApp.client_key == payload.client_key)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Douyin app already exists")
    app = DouyinApp(
        tenant_id=tenant_id,
        name=payload.name,
        client_key=payload.client_key,
        encrypted_client_secret=encrypt_payload({"client_secret": payload.client_secret}),
        is_active=True,
    )
    db.add(app)
    db.flush()
    log_audit(
        db,
        "douyin.app.create",
        "douyin_app",
        entity_id=app.id,
        tenant_id=tenant_id,
        user=user,
        payload={"name": payload.name, "client_key": payload.client_key},
    )
    db.commit()
    db.refresh(app)
    return app


def _load_client_secret(app: DouyinApp) -> str:
    return decrypt_payload(app.encrypted_client_secret)["client_secret"]


def list_accounts(db: Session, tenant_id: str) -> List[DouyinAccount]:
    stmt: Select = (
        select(DouyinAccount).where(DouyinAccount.tenant_id == tenant_id).order_by(DouyinAccount.created_at.desc())
    )
    return list(db.scalars(stmt).all())


async def import_account(db: Session, tenant_id: str, payload: DouyinAccountImport, user: User) -> DouyinAccount:
    app = db.get(DouyinApp, payload.app_id)
    if app is None or app.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin app not found")

    encrypted_access_token = encrypt_payload({"access_token": payload.access_token})
    encrypted_refresh_token = (
        encrypt_payload({"refresh_token": payload.refresh_token}) if payload.refresh_token else None
    )
    account = db.scalar(
        select(DouyinAccount).where(DouyinAccount.tenant_id == tenant_id, DouyinAccount.open_id == payload.open_id)
    )
    created = account is None
    if account is None:
        account = DouyinAccount(
            tenant_id=tenant_id,
            app_id=app.id,
            open_id=payload.open_id,
            nickname=payload.nickname or payload.open_id,
            avatar_url=payload.avatar_url,
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            access_token_expires_at=payload.access_token_expires_at,
            status=AccountStatus.active.value,
            last_validated_at=_utcnow(),
            last_error=None,
        )
        db.add(account)
        db.flush()
    else:
        account.app_id = app.id
        account.nickname = payload.nickname or account.nickname
        account.avatar_url = payload.avatar_url
        account.encrypted_access_token = encrypted_access_token
        account.encrypted_refresh_token = encrypted_refresh_token
        account.access_token_expires_at = payload.access_token_expires_at
        account.status = AccountStatus.active.value
        account.last_validated_at = _utcnow()
        account.last_error = None
        db.add(account)
        db.flush()

    log_audit(
        db,
        "douyin.account.import" if created else "douyin.account.update_token",
        "douyin_account",
        entity_id=account.id,
        tenant_id=tenant_id,
        user=user,
        payload={"open_id": account.open_id, "nickname": account.nickname, "app_id": app.id},
    )
    db.commit()
    db.refresh(account)
    await websocket_manager.broadcast(
        tenant_id,
        "douyin.account.updated",
        {"accountId": account.id, "nickname": account.nickname, "status": account.status},
    )
    return account


def start_oauth_session(
    db: Session,
    tenant_id: str,
    user: User,
    app_id: str,
    redirect_path: str,
) -> tuple[DouyinOAuthSession, str]:
    app = db.get(DouyinApp, app_id)
    if app is None or app.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin app not found")
    session = DouyinOAuthSession(
        tenant_id=tenant_id,
        user_id=user.id,
        app_id=app.id,
        state=str(uuid4()),
        redirect_path=redirect_path,
        expires_at=_utcnow() + timedelta(seconds=settings.douyin_oauth_state_ttl_seconds),
        status="pending",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    query = urlencode(
        {
            "client_key": app.client_key,
            "response_type": "code",
            "scope": settings.douyin_oauth_scopes,
            "redirect_uri": f"{settings.public_api_base_url.rstrip('/')}/api/douyin/oauth/callback",
            "state": session.state,
        }
    )
    auth_url = f"https://open.douyin.com/platform/oauth/connect/?{query}"
    return session, auth_url


async def exchange_code_for_account(
    db: Session,
    tenant_id: str,
    user: User,
    app_id: str,
    code: str,
) -> DouyinAccount:
    app = db.get(DouyinApp, app_id)
    if app is None or app.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin app not found")
    client_secret = _load_client_secret(app)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{DOUYIN_API_BASE}/oauth/access_token/",
            data={
                "client_key": app.client_key,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
    payload = response.json()
    if payload.get("err_no") not in (None, 0) or payload.get("error_code") not in (None, 0, "0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Douyin code exchange failed: {_extract_error_message(payload)}",
        )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    account = await import_account(
        db,
        tenant_id,
        DouyinAccountImport(
            app_id=app.id,
            open_id=data["open_id"],
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            nickname=data.get("open_id"),
            access_token_expires_at=_expires_at(data.get("expires_in")),
        ),
        user,
    )
    return account


def list_targets(db: Session, tenant_id: str) -> List[DouyinTarget]:
    stmt: Select = select(DouyinTarget).where(DouyinTarget.tenant_id == tenant_id).order_by(DouyinTarget.created_at.desc())
    return list(db.scalars(stmt).all())


def create_target(db: Session, tenant_id: str, payload: DouyinTargetCreate, user: User) -> DouyinTarget:
    account = db.get(DouyinAccount, payload.account_id)
    if account is None or account.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin account not found")
    existing = db.scalar(
        select(DouyinTarget).where(DouyinTarget.tenant_id == tenant_id, DouyinTarget.item_id == payload.item_id)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Douyin target already exists")
    target = DouyinTarget(
        tenant_id=tenant_id,
        account_id=payload.account_id,
        item_id=payload.item_id,
        title=payload.title,
        poll_interval=payload.poll_interval,
        status="active",
    )
    db.add(target)
    db.flush()
    log_audit(
        db,
        "douyin.target.create",
        "douyin_target",
        entity_id=target.id,
        tenant_id=tenant_id,
        user=user,
        payload={"item_id": target.item_id, "title": target.title},
    )
    db.commit()
    db.refresh(target)
    return target


def list_comments(
    db: Session,
    tenant_id: str,
    target_id: Optional[str] = None,
    is_handled: Optional[bool] = None,
) -> List[DouyinComment]:
    stmt: Select = select(DouyinComment).where(DouyinComment.tenant_id == tenant_id)
    if target_id:
        stmt = stmt.where(DouyinComment.target_id == target_id)
    if is_handled is not None:
        stmt = stmt.where(DouyinComment.is_handled.is_(is_handled))
    stmt = stmt.order_by(DouyinComment.posted_at.desc())
    return list(db.scalars(stmt).all())


def mark_comments_handled(
    db: Session,
    tenant_id: str,
    comment_ids: List[str],
    is_handled: bool,
    user: User,
) -> int:
    rows = db.scalars(
        select(DouyinComment).where(DouyinComment.tenant_id == tenant_id, DouyinComment.id.in_(comment_ids))
    ).all()
    changed_ids: List[str] = []
    for row in rows:
        if row.is_handled == is_handled:
            continue
        row.is_handled = is_handled
        db.add(row)
        changed_ids.append(row.id)
    if changed_ids:
        log_audit(
            db,
            "douyin.comment.handle.update",
            "douyin_comment",
            tenant_id=tenant_id,
            user=user,
            payload={"comment_ids": changed_ids, "is_handled": is_handled},
        )
    db.commit()
    return len(changed_ids)


def list_reply_actions(db: Session, tenant_id: str) -> List[DouyinReplyAction]:
    stmt: Select = (
        select(DouyinReplyAction)
        .where(DouyinReplyAction.tenant_id == tenant_id)
        .order_by(DouyinReplyAction.created_at.desc())
    )
    return list(db.scalars(stmt).all())


class DouyinGateway:
    def __init__(self) -> None:
        self._account_locks: Dict[str, Any] = {}

    def _lock_for_account(self, account_id: str) -> Any:
        import asyncio

        if account_id not in self._account_locks:
            self._account_locks[account_id] = asyncio.Lock()
        return self._account_locks[account_id]

    def load_access_token(self, account: DouyinAccount) -> str:
        return decrypt_payload(account.encrypted_access_token)["access_token"]

    def load_refresh_token(self, account: DouyinAccount) -> Optional[str]:
        if not account.encrypted_refresh_token:
            return None
        return decrypt_payload(account.encrypted_refresh_token)["refresh_token"]

    async def _request(
        self,
        method: str,
        path: str,
        access_token: str,
        *,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> dict:
        headers = {"access-token": access_token}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{DOUYIN_API_BASE}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )
            response.raise_for_status()
        payload = response.json()
        if payload.get("err_no") not in (None, 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Douyin API error {payload.get('err_no')}: {_extract_error_message(payload)}",
            )
        if payload.get("error_code") not in (None, 0, "0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Douyin API error {payload.get('error_code')}: {_extract_error_message(payload)}",
            )
        data = payload.get("data")
        return data if isinstance(data, dict) else payload

    async def refresh_account(self, db: Session, account: DouyinAccount) -> DouyinAccount:
        app = db.get(DouyinApp, account.app_id)
        if app is None or app.tenant_id != account.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin app not found")

        refresh_token = self.load_refresh_token(account)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Douyin refresh token missing; re-import authorization",
            )

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{DOUYIN_API_BASE}/oauth/refresh_token/",
                data={
                    "client_key": app.client_key,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        payload = response.json()
        if payload.get("err_no") not in (None, 0) or payload.get("error_code") not in (None, 0, "0"):
            account.status = AccountStatus.expired.value
            account.last_error = _extract_error_message(payload)
            account.last_validated_at = _utcnow()
            db.add(account)
            db.commit()
            db.refresh(account)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Douyin refresh failed: {_extract_error_message(payload)}",
            )

        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        account.encrypted_access_token = encrypt_payload({"access_token": data["access_token"]})
        if data.get("refresh_token"):
            account.encrypted_refresh_token = encrypt_payload({"refresh_token": data["refresh_token"]})
        account.access_token_expires_at = _expires_at(data.get("expires_in"))
        account.status = AccountStatus.active.value
        account.last_validated_at = _utcnow()
        account.last_error = None
        db.add(account)
        log_audit(
            db,
            "douyin.account.refresh",
            "douyin_account",
            entity_id=account.id,
            tenant_id=account.tenant_id,
            payload={"open_id": account.open_id, "nickname": account.nickname},
        )
        db.commit()
        db.refresh(account)
        await websocket_manager.broadcast(
            account.tenant_id,
            "douyin.account.updated",
            {"accountId": account.id, "nickname": account.nickname, "status": account.status},
        )
        return account

    async def poll_target_comments(self, db: Session, target: DouyinTarget) -> dict:
        account = db.get(DouyinAccount, target.account_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin account not found")

        task_run = start_task_run(
            db,
            task_name="poll_douyin_target_comments",
            task_kind="poll_comments",
            tenant_id=target.tenant_id,
            detail={"platform": "douyin", "target_id": target.id, "item_id": target.item_id},
        )
        db.commit()

        created_count = 0
        created_items: List[dict] = []
        access_token = self.load_access_token(account)
        try:
            async with self._lock_for_account(account.id):
                cursor: Any = 0
                page = 0
                while page < 5:
                    payload = await self._request(
                        "GET",
                        "/api/apps/v1/item/list_comment/",
                        access_token,
                        params={
                            "open_id": account.open_id,
                            "item_id": target.item_id,
                            "count": 20,
                            "cursor": cursor,
                            "sort_type": 1,
                        },
                    )
                    comments = payload.get("comments") or payload.get("comment_list") or payload.get("list") or []
                    if not comments:
                        break
                    for item in comments:
                        created_count += self._upsert_comment(db, target, account, item, True, None, created_items)
                        reply_total = int(item.get("reply_comment_total") or item.get("reply_count") or 0)
                        if reply_total <= 0:
                            continue
                        reply_cursor: Any = 0
                        reply_page = 0
                        while reply_page < 5:
                            reply_payload = await self._request(
                                "GET",
                                "/api/apps/v1/item/list_comment_reply/",
                                access_token,
                                params={
                                    "open_id": account.open_id,
                                    "item_id": target.item_id,
                                    "comment_id": item.get("comment_id"),
                                    "count": 20,
                                    "cursor": reply_cursor,
                                },
                            )
                            replies = (
                                reply_payload.get("comments")
                                or reply_payload.get("comment_list")
                                or reply_payload.get("list")
                                or []
                            )
                            if not replies:
                                break
                            for reply in replies:
                                created_count += self._upsert_comment(
                                    db,
                                    target,
                                    account,
                                    reply,
                                    False,
                                    str(item.get("comment_id") or ""),
                                    created_items,
                                )
                            if not reply_payload.get("has_more"):
                                break
                            reply_cursor = reply_payload.get("cursor") or reply_payload.get("next_cursor") or 0
                            reply_page += 1
                    if not payload.get("has_more"):
                        break
                    cursor = payload.get("cursor") or payload.get("next_cursor") or 0
                    page += 1

                target.last_polled_at = _utcnow()
                db.add(target)
                finish_task_run(
                    db,
                    task_run,
                    "success",
                    detail={"platform": "douyin", "created": created_count},
                )
                db.commit()
                await notify_new_comments(db, target.tenant_id, f"抖音作品 {target.title}", created_items)
                TARGET_POLLS_TOTAL.labels("success").inc()
                await websocket_manager.broadcast(
                    target.tenant_id,
                    "douyin.comments.polled",
                    {"targetId": target.id, "newComments": created_count, "timestamp": _utcnow().isoformat()},
                )
                return {"created": created_count}
        except Exception as exc:
            account.status = AccountStatus.expired.value if isinstance(exc, HTTPException) else account.status
            account.last_error = str(exc)
            db.add(account)
            finish_task_run(
                db,
                task_run,
                "failed",
                detail={"platform": "douyin", "item_id": target.item_id},
                error_message=str(exc),
            )
            db.commit()
            TARGET_POLLS_TOTAL.labels("failed").inc()
            raise

    def _upsert_comment(
        self,
        db: Session,
        target: DouyinTarget,
        account: DouyinAccount,
        item: dict,
        is_top_level: bool,
        parent_comment_id: Optional[str],
        created_items: List[dict],
    ) -> int:
        comment_id = str(item.get("comment_id") or item.get("id") or item.get("cid") or "")
        if not comment_id:
            return 0
        existing = db.scalar(
            select(DouyinComment).where(DouyinComment.target_id == target.id, DouyinComment.comment_id == comment_id)
        )
        payload = {
            "tenant_id": target.tenant_id,
            "target_id": target.id,
            "account_id": account.id,
            "comment_id": comment_id,
            "parent_comment_id": parent_comment_id,
            "user_open_id": item.get("comment_user_open_id") or item.get("user_open_id") or item.get("open_id"),
            "user_nickname": item.get("comment_user_nickname")
            or item.get("nickname")
            or item.get("nick_name")
            or "unknown",
            "user_avatar_url": item.get("comment_user_avatar_url") or item.get("avatar_url") or item.get("avatar"),
            "content": item.get("content") or item.get("text") or "",
            "posted_at": _parse_datetime(item.get("create_time") or item.get("comment_time") or item.get("timestamp")),
            "digg_count": int(item.get("digg_count") or item.get("like_count") or 0),
            "reply_count": int(item.get("reply_comment_total") or item.get("reply_count") or 0),
            "is_top_level": is_top_level,
            "raw_payload": item,
        }
        if existing is None:
            row = DouyinComment(**payload)
            db.add(row)
            db.flush()
            COMMENTS_DISCOVERED_TOTAL.labels("top_level" if is_top_level else "sub_reply").inc()
            created_items.append(
                {
                    "member_name": row.user_nickname,
                    "message": row.content,
                    "posted_at": row.posted_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "is_top_level": row.is_top_level,
                }
            )
            return 1
        existing.content = payload["content"]
        existing.digg_count = payload["digg_count"]
        existing.reply_count = payload["reply_count"]
        existing.user_nickname = payload["user_nickname"]
        existing.user_avatar_url = payload["user_avatar_url"]
        existing.user_open_id = payload["user_open_id"]
        existing.parent_comment_id = payload["parent_comment_id"]
        existing.posted_at = payload["posted_at"]
        existing.raw_payload = payload["raw_payload"]
        db.add(existing)
        return 0

    async def reply_to_comment(
        self,
        db: Session,
        tenant_id: str,
        account_id: str,
        comment_id: str,
        content: str,
        user: User,
    ) -> DouyinReplyAction:
        account = db.get(DouyinAccount, account_id)
        if account is None or account.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin account not found")
        comment = db.get(DouyinComment, comment_id)
        if comment is None or comment.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin comment not found")
        target = db.get(DouyinTarget, comment.target_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin target not found")

        action = DouyinReplyAction(
            tenant_id=tenant_id,
            account_id=account.id,
            comment_id=comment.id,
            operator_id=user.id,
            content=content,
            status=ReplyActionStatus.pending.value,
        )
        db.add(action)
        db.flush()
        log_audit(
            db,
            "douyin.reply.send.requested",
            "douyin_reply_action",
            entity_id=action.id,
            tenant_id=tenant_id,
            user=user,
            payload={"target_id": target.id, "comment_id": comment.id, "item_id": target.item_id},
        )
        db.commit()
        db.refresh(action)

        access_token = self.load_access_token(account)
        try:
            async with self._lock_for_account(account.id):
                response = await self._request(
                    "POST",
                    "/api/apps/v1/item/reply_comment/",
                    access_token,
                    params={"open_id": account.open_id},
                    json_body={
                        "item_id": target.item_id,
                        "comment_id": comment.comment_id,
                        "content": content,
                    },
                )
                action.status = ReplyActionStatus.sent.value
                action.response_payload = response
                action.sent_at = _utcnow()
                comment.is_replied = True
                comment.is_handled = True
                db.add(comment)
                REPLY_ACTIONS_TOTAL.labels("sent").inc()
        except Exception as exc:
            action.status = ReplyActionStatus.failed.value
            action.error_message = str(exc)
            account.last_error = str(exc)
            db.add(account)
            REPLY_ACTIONS_TOTAL.labels("failed").inc()

        db.add(action)
        log_audit(
            db,
            "douyin.reply.send.completed" if action.status == ReplyActionStatus.sent.value else "douyin.reply.send.failed",
            "douyin_reply_action",
            entity_id=action.id,
            tenant_id=tenant_id,
            user=user,
            payload={"comment_id": comment.id, "status": action.status, "error_message": action.error_message},
        )
        db.commit()
        db.refresh(action)
        await websocket_manager.broadcast(
            tenant_id,
            "douyin.reply.updated",
            {"replyActionId": action.id, "status": action.status},
        )
        return action


gateway = DouyinGateway()
