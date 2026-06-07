from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from bilibili_api import comment, creative_center, login_v2, user
from bilibili_api.comment import Comment, CommentResourceType, OrderType
from bilibili_api.utils.network import Credential

from app.core.crypto import decrypt_payload, encrypt_payload
from app.core.metrics import (
    COMMENTS_DISCOVERED_TOTAL,
    QR_LOGIN_EVENTS_TOTAL,
    REPLY_ACTIONS_TOTAL,
    TARGET_POLLS_TOTAL,
)
from app.models.entities import (
    AccountStatus,
    BilibiliAccount,
    BilibiliCredential,
    Comment as CommentModel,
    CommentEvent,
    CommentEventType,
    MonitorTarget,
    ReplyAction,
    ReplyActionStatus,
    RiskStatus,
)
from app.schemas.bilibili import BilibiliCredentialImport, QrCodeSessionOut, QrCodeStatusOut
from app.services.audit import log_audit
from app.services.notifications import notify_new_comments
from app.services.realtime import manager as websocket_manager
from app.services.task_runs import finish_task_run, start_task_run


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_payload_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


@dataclass
class QrSessionState:
    session_id: str
    tenant_id: str
    user_id: str
    qr: login_v2.QrCodeLogin
    created_at: datetime
    status: str = "pending"
    account_id: Optional[str] = None
    username: Optional[str] = None
    uid: Optional[int] = None
    detail: Optional[str] = None


class BilibiliGateway:
    def __init__(self) -> None:
        self._qr_sessions: Dict[str, QrSessionState] = {}
        self._account_locks: Dict[str, asyncio.Lock] = {}

    def _lock_for_account(self, account_id: str) -> asyncio.Lock:
        if account_id not in self._account_locks:
            self._account_locks[account_id] = asyncio.Lock()
        return self._account_locks[account_id]

    async def start_qr_login(self, tenant_id: str, user_id: str) -> QrCodeSessionOut:
        qr = login_v2.QrCodeLogin(platform=login_v2.QrCodeLoginChannel.WEB)
        await qr.generate_qrcode()
        QR_LOGIN_EVENTS_TOTAL.labels("started").inc()
        session_id = str(uuid4())
        picture = qr.get_qrcode_picture()
        image_b64 = base64.b64encode(picture.content).decode("utf-8")
        state = QrSessionState(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            qr=qr,
            created_at=_utcnow(),
        )
        self._qr_sessions[session_id] = state
        return QrCodeSessionOut(
            session_id=session_id,
            login_url=getattr(qr, "_QrCodeLogin__qr_link", ""),
            qr_terminal=qr.get_qrcode_terminal(),
            qr_image_base64=image_b64,
            status=state.status,
        )

    async def check_qr_login(self, db: Session, session_id: str, actor_id: str) -> QrCodeStatusOut:
        state = self._qr_sessions.get(session_id)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR session not found")
        event = await state.qr.check_state()
        state.status = event.name.lower()
        if event == login_v2.QrCodeLoginEvents.DONE:
            QR_LOGIN_EVENTS_TOTAL.labels("done").inc()
            credential = state.qr.get_credential()
            account = await self._upsert_account_from_credential(
                db=db,
                tenant_id=state.tenant_id,
                actor_id=actor_id,
                credential=credential,
            )
            state.account_id = account.id
            state.username = account.username
            state.uid = account.uid
            state.detail = "login completed"
        elif event == login_v2.QrCodeLoginEvents.TIMEOUT:
            QR_LOGIN_EVENTS_TOTAL.labels("timeout").inc()
            state.detail = "QR code timed out"
        return QrCodeStatusOut(
            session_id=state.session_id,
            status=state.status,
            account_id=state.account_id,
            username=state.username,
            uid=state.uid,
            detail=state.detail,
        )

    async def import_credentials(
        self,
        db: Session,
        tenant_id: str,
        actor_id: str,
        payload: BilibiliCredentialImport,
    ) -> BilibiliAccount:
        credential = Credential(
            sessdata=payload.sessdata,
            bili_jct=payload.bili_jct,
            buvid3=payload.buvid3,
            buvid4=payload.buvid4,
            dedeuserid=payload.dedeuserid,
            ac_time_value=payload.ac_time_value,
        )
        return await self._upsert_account_from_credential(db, tenant_id, actor_id, credential)

    async def refresh_account(self, db: Session, account: BilibiliAccount) -> BilibiliAccount:
        cred = self.load_credential(account)
        try:
            can_refresh = bool(cred.has_ac_time_value() and cred.has_bili_jct())
            if can_refresh and await cred.check_refresh():
                await cred.refresh()
            is_valid = await cred.check_valid()
            account.status = AccountStatus.active.value if is_valid else AccountStatus.expired.value
            account.last_refreshed_at = _utcnow()
            self.save_credential(db, account, cred)
        except Exception as exc:
            account.status = AccountStatus.expired.value
            account.last_error = str(exc)
        account.last_validated_at = _utcnow()
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def load_credential(self, account: BilibiliAccount) -> Credential:
        if account.credential is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account credential missing")
        payload = decrypt_payload(account.credential.encrypted_payload)
        return Credential(**payload)

    def save_credential(self, db: Session, account: BilibiliAccount, credential: Credential) -> None:
        payload = {
            "sessdata": credential.sessdata,
            "bili_jct": credential.bili_jct,
            "buvid3": credential.buvid3,
            "buvid4": credential.buvid4,
            "dedeuserid": credential.dedeuserid,
            "ac_time_value": credential.ac_time_value,
        }
        encrypted = encrypt_payload(payload)
        if account.credential is None:
            account.credential = BilibiliCredential(account_id=account.id, encrypted_payload=encrypted, is_active=True)
        else:
            account.credential.encrypted_payload = encrypted
            account.credential.rotated_at = _utcnow()
        db.add(account)
        db.flush()

    async def _upsert_account_from_credential(
        self,
        db: Session,
        tenant_id: str,
        actor_id: str,
        credential: Credential,
    ) -> BilibiliAccount:
        try:
            profile = await user.get_self_info(credential=credential)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Bilibili auth failed: {exc}") from exc

        uid = int(profile["mid"])
        account = db.scalar(
            select(BilibiliAccount).where(BilibiliAccount.tenant_id == tenant_id, BilibiliAccount.uid == uid)
        )
        created = account is None
        if account is None:
            account = BilibiliAccount(
                tenant_id=tenant_id,
                uid=uid,
                username=profile.get("name") or profile.get("uname") or str(uid),
                avatar_url=profile.get("face"),
                status=AccountStatus.active.value,
                risk_status=RiskStatus.normal.value,
            )
            db.add(account)
            db.flush()
        else:
            account.username = profile.get("name") or profile.get("uname") or account.username
            account.avatar_url = profile.get("face")
            account.status = AccountStatus.active.value
            account.last_error = None

        account.last_validated_at = _utcnow()
        account.last_refreshed_at = _utcnow()
        self.save_credential(db, account, credential)
        log_audit(
            db,
            "bilibili.account.bind" if created else "bilibili.account.refresh",
            "bilibili_account",
            entity_id=account.id,
            tenant_id=tenant_id,
            payload={"uid": uid, "username": account.username, "actor_id": actor_id},
        )
        db.commit()
        db.refresh(account)
        await websocket_manager.broadcast(
            tenant_id,
            "bilibili.account.updated",
            {"accountId": account.id, "username": account.username, "status": account.status},
        )
        return account

    async def import_video_targets(self, account: BilibiliAccount, max_pages: int = 5) -> List[Dict[str, Any]]:
        cred = self.load_credential(account)
        items: List[Dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            data = await creative_center.get_video_upload_manager_info(credential=cred, pn=page, ps=20)
            extracted = self._extract_videos(data)
            if not extracted:
                break
            items.extend(extracted)
            if len(extracted) < 20:
                break
            page += 1
        deduped = {}
        for item in items:
            deduped[item["bvid"]] = item
        return list(deduped.values())

    def _extract_videos(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for key in ("arc_audits", "archives", "list", "items"):
            raw_items = payload.get(key)
            if isinstance(raw_items, list):
                for item in raw_items:
                    bvid = item.get("bvid") or item.get("Archive") or item.get("archive", {}).get("bvid")
                    title = item.get("title") or item.get("archive", {}).get("title")
                    aid = item.get("aid") or item.get("archive", {}).get("aid")
                    owner_mid = item.get("mid") or item.get("archive", {}).get("mid")
                    if bvid and title and aid:
                        results.append(
                            {
                                "oid": int(aid),
                                "bvid": str(bvid),
                                "title": str(title),
                                "owner_mid": int(owner_mid) if owner_mid else None,
                            }
                        )
                if results:
                    return results
        for value in payload.values():
            if isinstance(value, dict):
                nested = self._extract_videos(value)
                if nested:
                    return nested
        return []

    async def poll_target_comments(self, db: Session, target: MonitorTarget) -> Dict[str, Any]:
        account = db.get(BilibiliAccount, target.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        task_run = start_task_run(
            db,
            task_name="poll_target_comments",
            task_kind="poll_comments",
            tenant_id=target.tenant_id,
            account_id=account.id,
            target_id=target.id,
            detail={"target": target.bvid},
        )
        db.commit()
        created_count = 0
        replies_count = 0
        created_items: List[Dict[str, Any]] = []
        try:
            async with self._lock_for_account(account.id):
                cred = self.load_credential(account)
                offset = ""
                page = 0
                while page < 5:
                    data = await comment.get_comments_lazy(
                        oid=target.oid,
                        type_=CommentResourceType.VIDEO,
                        offset=offset,
                        order=OrderType.TIME,
                        credential=cred,
                    )
                    replies = data.get("replies") or []
                    if not replies:
                        break
                    for item in replies:
                        main_created, main_payload = self._upsert_comment(
                            db,
                            target,
                            account,
                            item,
                            True,
                            event_type=CommentEventType.discovered.value,
                        )
                        created_count += main_created
                        if main_payload:
                            created_items.append(main_payload)
                        for sub_reply in item.get("replies") or []:
                            sub_created, sub_payload = self._upsert_comment(
                                db,
                                target,
                                account,
                                sub_reply,
                                False,
                                event_type=CommentEventType.discovered.value,
                            )
                            replies_count += sub_created
                            if sub_payload:
                                created_items.append(sub_payload)
                        reply_count = int(item.get("rcount") or 0)
                        loaded_subs = len(item.get("replies") or [])
                        if reply_count > loaded_subs:
                            comment_obj = Comment(
                                oid=target.oid,
                                type_=CommentResourceType.VIDEO,
                                rpid=int(item["rpid"]),
                                credential=cred,
                            )
                            sub_page = 1
                            while True:
                                sub_data = await comment_obj.get_sub_comments(page_index=sub_page, page_size=20)
                                sub_replies = sub_data.get("replies") or []
                                if not sub_replies:
                                    break
                                for sub_reply in sub_replies:
                                    sub_created, sub_payload = self._upsert_comment(
                                        db,
                                        target,
                                        account,
                                        sub_reply,
                                        False,
                                        event_type=CommentEventType.hydrated.value,
                                    )
                                    replies_count += sub_created
                                    if sub_payload:
                                        created_items.append(sub_payload)
                                if len(sub_replies) < 20:
                                    break
                                sub_page += 1
                    offset = data.get("cursor", {}).get("pagination_reply", {}).get("next_offset", "")
                    if not offset:
                        break
                    page += 1
                target.last_polled_at = _utcnow()
                db.add(target)
                finish_task_run(
                    db,
                    task_run,
                    "success",
                    detail={"created": created_count, "subReplies": replies_count},
                )
                db.commit()
                await notify_new_comments(db, target.tenant_id, target.title, created_items)
                TARGET_POLLS_TOTAL.labels("success").inc()
                await websocket_manager.broadcast(
                    target.tenant_id,
                    "comments.polled",
                    {
                        "targetId": target.id,
                        "newComments": created_count + replies_count,
                        "timestamp": _utcnow().isoformat(),
                    },
                )
                return {"created": created_count, "sub_replies": replies_count}
        except Exception as exc:
            finish_task_run(db, task_run, "failed", error_message=str(exc))
            db.commit()
            TARGET_POLLS_TOTAL.labels("failed").inc()
            raise

    def _upsert_comment(
        self,
        db: Session,
        target: MonitorTarget,
        account: BilibiliAccount,
        item: Dict[str, Any],
        is_top_level: bool,
        event_type: str = CommentEventType.discovered.value,
    ) -> tuple[int, Optional[Dict[str, Any]]]:
        rpid = int(item["rpid"])
        existing = db.scalar(
            select(CommentModel).where(CommentModel.target_id == target.id, CommentModel.rpid == rpid)
        )
        payload = {
            "tenant_id": target.tenant_id,
            "target_id": target.id,
            "account_id": account.id,
            "rpid": rpid,
            "root_rpid": int(item.get("root") or item.get("root_str") or item.get("parent") or 0) or None,
            "parent_rpid": int(item.get("parent") or item.get("parent_str") or 0) or None,
            "oid": target.oid,
            "member_mid": int(item.get("member", {}).get("mid") or 0) or None,
            "member_name": item.get("member", {}).get("uname") or "unknown",
            "message": item.get("content", {}).get("message") or "",
            "posted_at": datetime.fromtimestamp(int(item["ctime"]), tz=timezone.utc),
            "like_count": int(item.get("like") or 0),
            "is_top_level": is_top_level,
            "raw_payload": item,
        }
        if existing is None:
            comment_row = CommentModel(**payload)
            db.add(comment_row)
            db.flush()
            db.add(
                CommentEvent(
                    comment_id=comment_row.id,
                    event_type=event_type,
                    payload={
                        "message": comment_row.message,
                        "like_count": comment_row.like_count,
                        "member_name": comment_row.member_name,
                    },
                )
            )
            COMMENTS_DISCOVERED_TOTAL.labels("top_level" if comment_row.is_top_level else "sub_reply").inc()
            return 1, {
                "member_name": comment_row.member_name,
                "message": comment_row.message,
                "posted_at": comment_row.posted_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "is_top_level": comment_row.is_top_level,
            }
        changes = {}
        tracked_fields = (
            "message",
            "like_count",
            "member_name",
            "member_mid",
            "posted_at",
            "root_rpid",
            "parent_rpid",
        )
        for field in tracked_fields:
            old_value = getattr(existing, field)
            new_value = payload[field]
            if old_value != new_value:
                changes[field] = {
                    "from": _json_payload_value(old_value),
                    "to": _json_payload_value(new_value),
                }
                setattr(existing, field, new_value)
        existing.raw_payload = payload["raw_payload"]
        existing.oid = payload["oid"]
        existing.is_top_level = payload["is_top_level"]
        db.add(existing)
        if changes:
            db.add(
                CommentEvent(
                    comment_id=existing.id,
                    event_type=CommentEventType.updated.value,
                    payload=changes,
                )
            )
        return 0, None

    async def send_reply(
        self,
        db: Session,
        action: ReplyAction,
        account: BilibiliAccount,
        comment_row: CommentModel,
        content: str,
    ) -> ReplyAction:
        async with self._lock_for_account(account.id):
            cred = self.load_credential(account)
            if comment_row.is_top_level:
                root = comment_row.rpid
                parent = None
            else:
                root = comment_row.root_rpid or comment_row.parent_rpid or comment_row.rpid
                parent = comment_row.rpid
            request_payload = {
                "oid": comment_row.oid,
                "rpid": comment_row.rpid,
                "root_rpid": root,
                "parent_rpid": parent,
                "content": content,
            }
            action.request_payload = request_payload
            try:
                response = await comment.send_comment(
                    text=content,
                    oid=comment_row.oid,
                    type_=CommentResourceType.VIDEO,
                    root=root,
                    parent=parent,
                    credential=cred,
                )
                action.status = ReplyActionStatus.sent.value
                action.response_payload = response
                action.sent_at = _utcnow()
                comment_row.is_replied = True
                comment_row.is_handled = True
                db.add(comment_row)
                self.save_credential(db, account, cred)
                REPLY_ACTIONS_TOTAL.labels("sent").inc()
            except Exception as exc:
                action.status = ReplyActionStatus.failed.value
                action.error_message = str(exc)
                REPLY_ACTIONS_TOTAL.labels("failed").inc()
            db.add(action)
            db.commit()
            db.refresh(action)
            await websocket_manager.broadcast(
                account.tenant_id,
                "reply.updated",
                {"replyActionId": action.id, "status": action.status},
            )
            return action


gateway = BilibiliGateway()
