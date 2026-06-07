from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_payload, encrypt_payload
from app.core.metrics import COMMENTS_DISCOVERED_TOTAL, REPLY_ACTIONS_TOTAL, TARGET_POLLS_TOTAL
from app.models.entities import (
    AccountStatus,
    DouyinPersonalAccount,
    DouyinPersonalComment,
    DouyinPersonalLoginSession,
    DouyinPersonalReplyAction,
    DouyinPersonalTarget,
    ReplyActionStatus,
    User,
)
from app.schemas.douyin import DouyinPersonalCookieImport, DouyinPersonalTargetCreate
from app.services.audit import log_audit
from app.services.douyin_personal_helper import helper_client
from app.services.notifications import notify_new_comments
from app.services.realtime import manager as websocket_manager
from app.services.task_runs import finish_task_run, start_task_run


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _extract_profile(payload: dict[str, Any], fallback: Optional[DouyinPersonalCookieImport] = None) -> dict[str, Any]:
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else payload
    external_user_id = (
        profile.get("external_user_id")
        or profile.get("user_id")
        or profile.get("uid")
        or profile.get("sec_user_id")
        or profile.get("unique_id")
    )
    if not external_user_id and fallback and fallback.external_user_id:
        external_user_id = fallback.external_user_id
    if not external_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Douyin personal profile missing external user id")
    nickname = profile.get("nickname") or profile.get("nick_name") or profile.get("display_name")
    if not nickname and fallback and fallback.nickname:
        nickname = fallback.nickname
    avatar_url = profile.get("avatar_url") or profile.get("avatar") or profile.get("avatar_thumb")
    if not avatar_url and fallback and fallback.avatar_url:
        avatar_url = fallback.avatar_url
    return {
        "external_user_id": str(external_user_id),
        "nickname": nickname or str(external_user_id),
        "avatar_url": avatar_url,
    }


def _extract_cookie(payload: dict[str, Any], fallback_cookie: Optional[str] = None) -> str:
    cookie = payload.get("cookie") or payload.get("cookie_string") or fallback_cookie
    if not cookie:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Douyin personal helper did not return cookie")
    return str(cookie)


def _extract_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    runtime = payload.get("runtime")
    if isinstance(runtime, dict):
        return runtime
    return {}


def _extract_target(payload: dict[str, Any], requested: DouyinPersonalTargetCreate) -> dict[str, str]:
    aweme_id = payload.get("aweme_id") or payload.get("item_id") or requested.aweme_id
    if not aweme_id and requested.video_url:
        parsed = urlparse(requested.video_url)
        pieces = [part for part in parsed.path.split("/") if part]
        if "video" in pieces:
            idx = pieces.index("video")
            if idx + 1 < len(pieces):
                aweme_id = pieces[idx + 1]
    if not aweme_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to resolve Douyin aweme_id")
    title = payload.get("title") or requested.title or f"抖音个人作品 {aweme_id}"
    video_url = payload.get("video_url") or requested.video_url or f"https://www.douyin.com/video/{aweme_id}"
    return {"aweme_id": str(aweme_id), "title": str(title), "video_url": str(video_url)}


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    if isinstance(value, str):
        if value.isdigit():
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return _utcnow()
    return _utcnow()


def _comment_user_id(item: dict[str, Any]) -> Optional[str]:
    value = (
        item.get("comment_user_open_id")
        or item.get("user_open_id")
        or item.get("open_id")
        or item.get("uid")
        or item.get("user_id")
        or item.get("sec_uid")
    )
    return str(value) if value not in (None, "") else None


def _comment_nickname(item: dict[str, Any]) -> str:
    return str(
        item.get("comment_user_nickname")
        or item.get("user_nickname")
        or item.get("nickname")
        or item.get("nick_name")
        or "unknown"
    )


def _comment_avatar(item: dict[str, Any]) -> Optional[str]:
    value = item.get("comment_user_avatar_url") or item.get("user_avatar_url") or item.get("avatar_url") or item.get("avatar")
    return str(value) if value not in (None, "") else None


def list_accounts(db: Session, tenant_id: str) -> List[DouyinPersonalAccount]:
    stmt: Select = (
        select(DouyinPersonalAccount)
        .where(DouyinPersonalAccount.tenant_id == tenant_id)
        .order_by(DouyinPersonalAccount.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def load_cookie(account: DouyinPersonalAccount) -> str:
    return str(decrypt_payload(account.encrypted_cookie_payload)["cookie"])


def load_runtime(account: DouyinPersonalAccount) -> dict[str, Any]:
    payload = decrypt_payload(account.encrypted_runtime_payload)
    return payload if isinstance(payload, dict) else {}


def _apply_account_payload(
    account: DouyinPersonalAccount,
    *,
    cookie: str,
    runtime: dict[str, Any],
    profile: dict[str, Any],
) -> DouyinPersonalAccount:
    account.nickname = str(profile["nickname"])
    account.avatar_url = profile.get("avatar_url")
    account.external_user_id = str(profile["external_user_id"])
    account.encrypted_cookie_payload = encrypt_payload({"cookie": cookie})
    account.encrypted_runtime_payload = encrypt_payload(runtime)
    account.status = AccountStatus.active.value
    account.last_validated_at = _utcnow()
    account.last_error = None
    return account


def _upsert_account(
    db: Session,
    tenant_id: str,
    *,
    cookie: str,
    runtime: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[DouyinPersonalAccount, bool]:
    account = db.scalar(
        select(DouyinPersonalAccount).where(
            DouyinPersonalAccount.tenant_id == tenant_id,
            DouyinPersonalAccount.external_user_id == str(profile["external_user_id"]),
        )
    )
    created = account is None
    if account is None:
        account = DouyinPersonalAccount(
            tenant_id=tenant_id,
            nickname=str(profile["nickname"]),
            avatar_url=profile.get("avatar_url"),
            external_user_id=str(profile["external_user_id"]),
            encrypted_cookie_payload=encrypt_payload({"cookie": cookie}),
            encrypted_runtime_payload=encrypt_payload(runtime),
            status=AccountStatus.active.value,
            last_validated_at=_utcnow(),
        )
        db.add(account)
        db.flush()
    else:
        _apply_account_payload(account, cookie=cookie, runtime=runtime, profile=profile)
        db.add(account)
        db.flush()
    return account, created


async def start_login_session(db: Session, tenant_id: str, user: User) -> DouyinPersonalLoginSession:
    payload = await helper_client.start_login_session()
    helper_session_id = str(payload.get("session_id") or payload.get("helper_session_id") or "")
    if not helper_session_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Douyin personal helper did not return session id")
    session = DouyinPersonalLoginSession(
        tenant_id=tenant_id,
        user_id=user.id,
        helper_session_id=helper_session_id,
        login_url=payload.get("login_url"),
        qr_image_base64=payload.get("qr_image_base64"),
        status=str(payload.get("status") or "pending"),
        expires_at=_utcnow() + timedelta(seconds=settings.douyin_personal_login_session_ttl_seconds),
    )
    db.add(session)
    log_audit(
        db,
        "douyin.personal.login.start",
        "douyin_personal_login_session",
        entity_id=session.id,
        tenant_id=tenant_id,
        user=user,
        payload={"helper_session_id": helper_session_id},
    )
    db.commit()
    db.refresh(session)
    return session


async def get_login_session_status(
    db: Session,
    tenant_id: str,
    session_id: str,
    user: User,
) -> dict[str, Any]:
    session = db.get(DouyinPersonalLoginSession, session_id)
    if session is None or session.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin personal login session not found")
    expires_at = _as_utc(session.expires_at)
    consumed_at = _as_utc(session.consumed_at)
    if expires_at is not None and expires_at < _utcnow() and consumed_at is None:
        session.status = "expired"
        db.add(session)
        db.commit()
    if session.status == "done":
        account = db.get(DouyinPersonalAccount, session.account_id) if session.account_id else None
        return {
            "session_id": session.id,
            "helper_session_id": session.helper_session_id,
            "status": session.status,
            "account_id": session.account_id,
            "nickname": account.nickname if account else None,
            "external_user_id": account.external_user_id if account else None,
            "detail": session.last_error,
        }

    payload = await helper_client.get_login_session(session.helper_session_id)
    session.status = str(payload.get("status") or session.status)
    session.login_url = payload.get("login_url") or session.login_url
    session.qr_image_base64 = payload.get("qr_image_base64") or session.qr_image_base64
    session.last_error = payload.get("detail") or payload.get("error")

    account = db.get(DouyinPersonalAccount, session.account_id) if session.account_id else None
    if session.status == "done" and consumed_at is None:
        profile = _extract_profile(payload)
        cookie = _extract_cookie(payload)
        runtime = _extract_runtime(payload)
        account, created = _upsert_account(db, tenant_id, cookie=cookie, runtime=runtime, profile=profile)
        session.account_id = account.id
        session.consumed_at = _utcnow()
        db.add(session)
        log_audit(
            db,
            "douyin.personal.login.completed",
            "douyin_personal_account",
            entity_id=account.id,
            tenant_id=tenant_id,
            user=user,
            payload={"external_user_id": account.external_user_id, "created": created},
        )
        await websocket_manager.broadcast(
            tenant_id,
            "douyin.personal.account.updated",
            {"accountId": account.id, "nickname": account.nickname, "status": account.status},
        )
    db.commit()
    if session.account_id:
        account = db.get(DouyinPersonalAccount, session.account_id)
    return {
        "session_id": session.id,
        "helper_session_id": session.helper_session_id,
        "status": session.status,
        "account_id": session.account_id,
        "nickname": account.nickname if account else None,
        "external_user_id": account.external_user_id if account else None,
        "detail": session.last_error,
    }


async def import_cookie_account(
    db: Session,
    tenant_id: str,
    payload: DouyinPersonalCookieImport,
    user: User,
) -> DouyinPersonalAccount:
    normalized = await helper_client.normalize_cookie(payload.cookie)
    profile = _extract_profile(normalized, payload)
    cookie = _extract_cookie(normalized, payload.cookie)
    runtime = _extract_runtime(normalized)
    account, created = _upsert_account(db, tenant_id, cookie=cookie, runtime=runtime, profile=profile)
    db.add(account)
    log_audit(
        db,
        "douyin.personal.account.import" if created else "douyin.personal.account.update_cookie",
        "douyin_personal_account",
        entity_id=account.id,
        tenant_id=tenant_id,
        user=user,
        payload={"external_user_id": account.external_user_id, "nickname": account.nickname},
    )
    db.commit()
    db.refresh(account)
    await websocket_manager.broadcast(
        tenant_id,
        "douyin.personal.account.updated",
        {"accountId": account.id, "nickname": account.nickname, "status": account.status},
    )
    return account


async def refresh_runtime(
    db: Session,
    account: DouyinPersonalAccount,
    user: Optional[User],
) -> DouyinPersonalAccount:
    payload = await helper_client.refresh_runtime(load_cookie(account), load_runtime(account))
    profile = _extract_profile(payload)
    cookie = _extract_cookie(payload, load_cookie(account))
    runtime = _extract_runtime(payload)
    _apply_account_payload(account, cookie=cookie, runtime=runtime, profile=profile)
    db.add(account)
    log_audit(
        db,
        "douyin.personal.account.refresh_runtime",
        "douyin_personal_account",
        entity_id=account.id,
        tenant_id=account.tenant_id,
        user=user,
        payload={"external_user_id": account.external_user_id, "nickname": account.nickname},
    )
    db.commit()
    db.refresh(account)
    await websocket_manager.broadcast(
        account.tenant_id,
        "douyin.personal.account.updated",
        {"accountId": account.id, "nickname": account.nickname, "status": account.status},
    )
    return account


def list_targets(db: Session, tenant_id: str) -> List[DouyinPersonalTarget]:
    stmt: Select = (
        select(DouyinPersonalTarget)
        .where(DouyinPersonalTarget.tenant_id == tenant_id)
        .order_by(DouyinPersonalTarget.created_at.desc())
    )
    return list(db.scalars(stmt).all())


async def create_target(
    db: Session,
    tenant_id: str,
    payload: DouyinPersonalTargetCreate,
    user: User,
) -> DouyinPersonalTarget:
    account = db.get(DouyinPersonalAccount, payload.account_id)
    if account is None or account.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin personal account not found")
    resolved = _extract_target(
        await helper_client.resolve_target(
            cookie=load_cookie(account),
            runtime=load_runtime(account),
            aweme_id=payload.aweme_id,
            video_url=payload.video_url,
            title=payload.title,
        ),
        payload,
    )
    existing = db.scalar(
        select(DouyinPersonalTarget).where(
            DouyinPersonalTarget.tenant_id == tenant_id,
            DouyinPersonalTarget.aweme_id == resolved["aweme_id"],
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Douyin personal target already exists")
    target = DouyinPersonalTarget(
        tenant_id=tenant_id,
        account_id=account.id,
        aweme_id=resolved["aweme_id"],
        video_url=resolved["video_url"],
        title=resolved["title"],
        poll_interval=payload.poll_interval,
        status="active",
    )
    db.add(target)
    db.flush()
    log_audit(
        db,
        "douyin.personal.target.create",
        "douyin_personal_target",
        entity_id=target.id,
        tenant_id=tenant_id,
        user=user,
        payload={"aweme_id": target.aweme_id, "title": target.title},
    )
    db.commit()
    db.refresh(target)
    return target


def list_comments(
    db: Session,
    tenant_id: str,
    target_id: Optional[str] = None,
    is_handled: Optional[bool] = None,
) -> List[DouyinPersonalComment]:
    stmt: Select = select(DouyinPersonalComment).where(DouyinPersonalComment.tenant_id == tenant_id)
    if target_id:
        stmt = stmt.where(DouyinPersonalComment.target_id == target_id)
    if is_handled is not None:
        stmt = stmt.where(DouyinPersonalComment.is_handled.is_(is_handled))
    stmt = stmt.order_by(DouyinPersonalComment.posted_at.desc())
    return list(db.scalars(stmt).all())


def mark_comments_handled(
    db: Session,
    tenant_id: str,
    comment_ids: List[str],
    is_handled: bool,
    user: User,
) -> int:
    rows = db.scalars(
        select(DouyinPersonalComment).where(
            DouyinPersonalComment.tenant_id == tenant_id,
            DouyinPersonalComment.id.in_(comment_ids),
        )
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
            "douyin.personal.comment.handle.update",
            "douyin_personal_comment",
            tenant_id=tenant_id,
            user=user,
            payload={"comment_ids": changed_ids, "is_handled": is_handled},
        )
    db.commit()
    return len(changed_ids)


def list_reply_actions(db: Session, tenant_id: str) -> List[DouyinPersonalReplyAction]:
    stmt: Select = (
        select(DouyinPersonalReplyAction)
        .where(DouyinPersonalReplyAction.tenant_id == tenant_id)
        .order_by(DouyinPersonalReplyAction.created_at.desc())
    )
    return list(db.scalars(stmt).all())


class DouyinPersonalGateway:
    async def poll_target_comments(self, db: Session, target: DouyinPersonalTarget) -> dict[str, Any]:
        account = db.get(DouyinPersonalAccount, target.account_id)
        if account is None or account.tenant_id != target.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin personal account not found")

        task_run = start_task_run(
            db,
            task_name="poll_douyin_personal_target_comments",
            task_kind="poll_comments",
            tenant_id=target.tenant_id,
            detail={"platform": "douyin", "integration_type": "personal", "target_id": target.id, "aweme_id": target.aweme_id},
        )
        db.commit()

        created_count = 0
        created_items: List[dict[str, Any]] = []
        try:
            payload = await helper_client.fetch_comments(
                cookie=load_cookie(account),
                runtime=load_runtime(account),
                aweme_id=target.aweme_id,
            )
            rows = payload.get("comments") if isinstance(payload, dict) else payload
            comments = rows if isinstance(rows, list) else []
            for item in comments:
                created_count += self._upsert_comment(db, target, account, item, True, None, created_items)
                replies = item.get("reply_comments") or item.get("reply_comment") or item.get("replies") or []
                if not isinstance(replies, list):
                    continue
                parent_comment_id = str(item.get("comment_id") or item.get("id") or item.get("cid") or "")
                for reply in replies:
                    created_count += self._upsert_comment(
                        db,
                        target,
                        account,
                        reply,
                        False,
                        parent_comment_id or None,
                        created_items,
                    )
            target.last_polled_at = _utcnow()
            db.add(target)
            finish_task_run(
                db,
                task_run,
                "success",
                detail={"platform": "douyin", "integration_type": "personal", "created": created_count},
            )
            db.commit()
            if created_items:
                await notify_new_comments(db, target.tenant_id, f"抖音个人作品 {target.title}", created_items)
            TARGET_POLLS_TOTAL.labels("success").inc()
            await websocket_manager.broadcast(
                target.tenant_id,
                "douyin.personal.comments.polled",
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
                detail={"platform": "douyin", "integration_type": "personal", "aweme_id": target.aweme_id},
                error_message=str(exc),
            )
            db.commit()
            TARGET_POLLS_TOTAL.labels("failed").inc()
            raise

    def _upsert_comment(
        self,
        db: Session,
        target: DouyinPersonalTarget,
        account: DouyinPersonalAccount,
        item: dict[str, Any],
        is_top_level: bool,
        parent_comment_id: Optional[str],
        created_items: List[dict[str, Any]],
    ) -> int:
        comment_id = str(item.get("comment_id") or item.get("id") or item.get("cid") or "")
        if not comment_id:
            return 0
        existing = db.scalar(
            select(DouyinPersonalComment).where(
                DouyinPersonalComment.target_id == target.id,
                DouyinPersonalComment.comment_id == comment_id,
            )
        )
        payload = {
            "tenant_id": target.tenant_id,
            "target_id": target.id,
            "account_id": account.id,
            "comment_id": comment_id,
            "parent_comment_id": parent_comment_id,
            "user_external_id": _comment_user_id(item),
            "user_nickname": _comment_nickname(item),
            "user_avatar_url": _comment_avatar(item),
            "content": str(item.get("content") or item.get("text") or ""),
            "posted_at": _parse_datetime(item.get("create_time") or item.get("comment_time") or item.get("timestamp")),
            "digg_count": int(item.get("digg_count") or item.get("like_count") or 0),
            "reply_count": int(item.get("reply_comment_total") or item.get("reply_count") or 0),
            "is_top_level": is_top_level,
            "raw_payload": item,
        }
        if existing is None:
            row = DouyinPersonalComment(**payload)
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
        existing.parent_comment_id = payload["parent_comment_id"]
        existing.user_external_id = payload["user_external_id"]
        existing.user_nickname = payload["user_nickname"]
        existing.user_avatar_url = payload["user_avatar_url"]
        existing.content = payload["content"]
        existing.posted_at = payload["posted_at"]
        existing.digg_count = payload["digg_count"]
        existing.reply_count = payload["reply_count"]
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
    ) -> DouyinPersonalReplyAction:
        account = db.get(DouyinPersonalAccount, account_id)
        if account is None or account.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin personal account not found")
        comment = db.get(DouyinPersonalComment, comment_id)
        if comment is None or comment.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin personal comment not found")
        target = db.get(DouyinPersonalTarget, comment.target_id)
        if target is None or target.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Douyin personal target not found")

        action = DouyinPersonalReplyAction(
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
            "douyin.personal.reply.send.requested",
            "douyin_personal_reply_action",
            entity_id=action.id,
            tenant_id=tenant_id,
            user=user,
            payload={"target_id": target.id, "comment_id": comment.id, "aweme_id": target.aweme_id},
        )
        db.commit()
        db.refresh(action)

        try:
            response = await helper_client.reply_comment(
                cookie=load_cookie(account),
                runtime=load_runtime(account),
                aweme_id=target.aweme_id,
                comment_id=comment.comment_id,
                comment_text=comment.content,
                comment_author=comment.user_nickname,
                content=content,
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
            "douyin.personal.reply.send.completed"
            if action.status == ReplyActionStatus.sent.value
            else "douyin.personal.reply.send.failed",
            "douyin_personal_reply_action",
            entity_id=action.id,
            tenant_id=tenant_id,
            user=user,
            payload={"comment_id": comment.id, "status": action.status, "error_message": action.error_message},
        )
        db.commit()
        db.refresh(action)
        await websocket_manager.broadcast(
            tenant_id,
            "douyin.personal.reply.updated",
            {"replyActionId": action.id, "status": action.status},
        )
        return action


gateway = DouyinPersonalGateway()
