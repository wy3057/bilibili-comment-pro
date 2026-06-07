from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    BilibiliAccount,
    Comment,
    DouyinAccount,
    DouyinComment,
    DouyinPersonalAccount,
    DouyinPersonalComment,
    DouyinPersonalReplyAction,
    DouyinPersonalTarget,
    DouyinReplyAction,
    DouyinTarget,
    MonitorTarget,
    ReplyAction,
    ReplyDraft,
)
from app.schemas.ops import (
    PlatformAccountOut,
    PlatformCommentDetailOut,
    PlatformCommentEventOut,
    PlatformCommentOut,
    PlatformReplyActionOut,
    PlatformReplyDraftOut,
    PlatformReplySendRequest,
    PlatformTargetOut,
)
from app.services import ai_reply as ai_reply_service
from app.services import comments as comment_service
from app.services import douyin as douyin_service
from app.services import douyin_personal as douyin_personal_service
from app.services import replies as reply_service
from app.services.audit import log_audit


def _match_keyword(value: str, keyword: Optional[str]) -> bool:
    if not keyword:
        return True
    return keyword.lower() in value.lower()


def _map_bilibili_account(account: BilibiliAccount) -> PlatformAccountOut:
    return PlatformAccountOut(
        id=account.id,
        created_at=account.created_at,
        updated_at=account.updated_at,
        platform="bilibili",
        integration_type=None,
        tenant_id=account.tenant_id,
        display_name=account.username,
        external_id=str(account.uid),
        avatar_url=account.avatar_url,
        status=account.status,
        risk_status=account.risk_status,
        last_validated_at=account.last_validated_at,
        last_refreshed_at=account.last_refreshed_at,
        access_token_expires_at=None,
        last_error=account.last_error,
    )


def _map_douyin_account(account: DouyinAccount) -> PlatformAccountOut:
    return PlatformAccountOut(
        id=account.id,
        created_at=account.created_at,
        updated_at=account.updated_at,
        platform="douyin",
        integration_type="enterprise",
        tenant_id=account.tenant_id,
        display_name=account.nickname,
        external_id=account.open_id,
        avatar_url=account.avatar_url,
        status=account.status,
        risk_status=None,
        last_validated_at=account.last_validated_at,
        last_refreshed_at=None,
        access_token_expires_at=account.access_token_expires_at,
        last_error=account.last_error,
    )


def _map_douyin_personal_account(account: DouyinPersonalAccount) -> PlatformAccountOut:
    return PlatformAccountOut(
        id=account.id,
        created_at=account.created_at,
        updated_at=account.updated_at,
        platform="douyin",
        integration_type="personal",
        tenant_id=account.tenant_id,
        display_name=account.nickname,
        external_id=account.external_user_id,
        avatar_url=account.avatar_url,
        status=account.status,
        risk_status=None,
        last_validated_at=account.last_validated_at,
        last_refreshed_at=None,
        access_token_expires_at=None,
        last_error=account.last_error,
    )


def list_accounts(
    db: Session,
    tenant_id: str,
    platform: Optional[str] = None,
    integration_type: Optional[str] = None,
) -> list[PlatformAccountOut]:
    items: list[PlatformAccountOut] = []
    if platform in (None, "all", "bilibili"):
        accounts = db.scalars(select(BilibiliAccount).where(BilibiliAccount.tenant_id == tenant_id)).all()
        items.extend(_map_bilibili_account(item) for item in accounts)
    if platform in (None, "all", "douyin"):
        if integration_type in (None, "all", "enterprise"):
            accounts = db.scalars(select(DouyinAccount).where(DouyinAccount.tenant_id == tenant_id)).all()
            items.extend(_map_douyin_account(item) for item in accounts)
        if integration_type in (None, "all", "personal"):
            accounts = db.scalars(select(DouyinPersonalAccount).where(DouyinPersonalAccount.tenant_id == tenant_id)).all()
            items.extend(_map_douyin_personal_account(item) for item in accounts)
    return sorted(items, key=lambda item: item.created_at, reverse=True)


def _map_bilibili_target(target: MonitorTarget) -> PlatformTargetOut:
    return PlatformTargetOut(
        id=target.id,
        created_at=target.created_at,
        updated_at=target.updated_at,
        platform="bilibili",
        integration_type=None,
        tenant_id=target.tenant_id,
        account_id=target.account_id,
        title=target.title,
        external_id=target.bvid,
        status=target.status,
        poll_interval=target.poll_interval,
        last_polled_at=target.last_polled_at,
    )


def _map_douyin_target(target: DouyinTarget) -> PlatformTargetOut:
    return PlatformTargetOut(
        id=target.id,
        created_at=target.created_at,
        updated_at=target.updated_at,
        platform="douyin",
        integration_type="enterprise",
        tenant_id=target.tenant_id,
        account_id=target.account_id,
        title=target.title,
        external_id=target.item_id,
        status=target.status,
        poll_interval=target.poll_interval,
        last_polled_at=target.last_polled_at,
    )


def _map_douyin_personal_target(target: DouyinPersonalTarget) -> PlatformTargetOut:
    return PlatformTargetOut(
        id=target.id,
        created_at=target.created_at,
        updated_at=target.updated_at,
        platform="douyin",
        integration_type="personal",
        tenant_id=target.tenant_id,
        account_id=target.account_id,
        title=target.title,
        external_id=target.aweme_id,
        status=target.status,
        poll_interval=target.poll_interval,
        last_polled_at=target.last_polled_at,
    )


def list_targets(
    db: Session,
    tenant_id: str,
    platform: Optional[str] = None,
    integration_type: Optional[str] = None,
) -> list[PlatformTargetOut]:
    items: list[PlatformTargetOut] = []
    if platform in (None, "all", "bilibili"):
        items.extend(
            _map_bilibili_target(item)
            for item in db.scalars(select(MonitorTarget).where(MonitorTarget.tenant_id == tenant_id)).all()
        )
    if platform in (None, "all", "douyin"):
        if integration_type in (None, "all", "enterprise"):
            items.extend(
                _map_douyin_target(item)
                for item in db.scalars(select(DouyinTarget).where(DouyinTarget.tenant_id == tenant_id)).all()
            )
        if integration_type in (None, "all", "personal"):
            items.extend(
                _map_douyin_personal_target(item)
                for item in db.scalars(select(DouyinPersonalTarget).where(DouyinPersonalTarget.tenant_id == tenant_id)).all()
            )
    return sorted(items, key=lambda item: item.created_at, reverse=True)


def _map_bilibili_comment(comment: Comment) -> PlatformCommentOut:
    return PlatformCommentOut(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        platform="bilibili",
        integration_type=None,
        tenant_id=comment.tenant_id,
        target_id=comment.target_id,
        account_id=comment.account_id,
        external_id=str(comment.rpid),
        parent_external_id=str(comment.parent_rpid) if comment.parent_rpid is not None else None,
        author_name=comment.member_name,
        author_avatar_url=None,
        content=comment.message,
        posted_at=comment.posted_at,
        like_count=comment.like_count,
        reply_count=0,
        is_top_level=comment.is_top_level,
        is_handled=comment.is_handled,
        is_replied=comment.is_replied,
        raw_payload=comment.raw_payload,
    )


def _map_douyin_comment(comment: DouyinComment) -> PlatformCommentOut:
    return PlatformCommentOut(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        platform="douyin",
        integration_type="enterprise",
        tenant_id=comment.tenant_id,
        target_id=comment.target_id,
        account_id=comment.account_id,
        external_id=comment.comment_id,
        parent_external_id=comment.parent_comment_id,
        author_name=comment.user_nickname,
        author_avatar_url=comment.user_avatar_url,
        content=comment.content,
        posted_at=comment.posted_at,
        like_count=comment.digg_count,
        reply_count=comment.reply_count,
        is_top_level=comment.is_top_level,
        is_handled=comment.is_handled,
        is_replied=comment.is_replied,
        raw_payload=comment.raw_payload,
    )


def _map_douyin_personal_comment(comment: DouyinPersonalComment) -> PlatformCommentOut:
    return PlatformCommentOut(
        id=comment.id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        platform="douyin",
        integration_type="personal",
        tenant_id=comment.tenant_id,
        target_id=comment.target_id,
        account_id=comment.account_id,
        external_id=comment.comment_id,
        parent_external_id=comment.parent_comment_id,
        author_name=comment.user_nickname,
        author_avatar_url=comment.user_avatar_url,
        content=comment.content,
        posted_at=comment.posted_at,
        like_count=comment.digg_count,
        reply_count=comment.reply_count,
        is_top_level=comment.is_top_level,
        is_handled=comment.is_handled,
        is_replied=comment.is_replied,
        raw_payload=comment.raw_payload,
    )


def list_comments(
    db: Session,
    tenant_id: str,
    *,
    platform: Optional[str] = None,
    integration_type: Optional[str] = None,
    target_id: Optional[str] = None,
    account_id: Optional[str] = None,
    is_handled: Optional[bool] = None,
    is_replied: Optional[bool] = None,
    keyword: Optional[str] = None,
) -> list[PlatformCommentOut]:
    items: list[PlatformCommentOut] = []
    if platform in (None, "all", "bilibili"):
        rows = db.scalars(select(Comment).where(Comment.tenant_id == tenant_id)).all()
        for row in rows:
            if target_id and row.target_id != target_id:
                continue
            if account_id and row.account_id != account_id:
                continue
            if is_handled is not None and row.is_handled != is_handled:
                continue
            if is_replied is not None and row.is_replied != is_replied:
                continue
            if not _match_keyword(f"{row.member_name} {row.message} {row.rpid}", keyword):
                continue
            items.append(_map_bilibili_comment(row))
    if platform in (None, "all", "douyin"):
        if integration_type in (None, "all", "enterprise"):
            rows = db.scalars(select(DouyinComment).where(DouyinComment.tenant_id == tenant_id)).all()
            for row in rows:
                if target_id and row.target_id != target_id:
                    continue
                if account_id and row.account_id != account_id:
                    continue
                if is_handled is not None and row.is_handled != is_handled:
                    continue
                if is_replied is not None and row.is_replied != is_replied:
                    continue
                if not _match_keyword(f"{row.user_nickname} {row.content} {row.comment_id}", keyword):
                    continue
                items.append(_map_douyin_comment(row))
        if integration_type in (None, "all", "personal"):
            rows = db.scalars(select(DouyinPersonalComment).where(DouyinPersonalComment.tenant_id == tenant_id)).all()
            for row in rows:
                if target_id and row.target_id != target_id:
                    continue
                if account_id and row.account_id != account_id:
                    continue
                if is_handled is not None and row.is_handled != is_handled:
                    continue
                if is_replied is not None and row.is_replied != is_replied:
                    continue
                if not _match_keyword(f"{row.user_nickname} {row.content} {row.comment_id}", keyword):
                    continue
                items.append(_map_douyin_personal_comment(row))
    return sorted(items, key=lambda item: item.posted_at, reverse=True)


def _map_bilibili_reply_action(action: ReplyAction) -> PlatformReplyActionOut:
    content = action.request_payload.get("content") if isinstance(action.request_payload, dict) else None
    return PlatformReplyActionOut(
        id=action.id,
        created_at=action.created_at,
        updated_at=action.updated_at,
        platform="bilibili",
        integration_type=None,
        tenant_id=action.tenant_id,
        account_id=action.account_id,
        comment_id=action.comment_id,
        status=action.status,
        error_message=action.error_message,
        sent_at=action.sent_at,
        content=str(content) if content is not None else None,
    )


def _map_douyin_reply_action(action: DouyinReplyAction) -> PlatformReplyActionOut:
    return PlatformReplyActionOut(
        id=action.id,
        created_at=action.created_at,
        updated_at=action.updated_at,
        platform="douyin",
        integration_type="enterprise",
        tenant_id=action.tenant_id,
        account_id=action.account_id,
        comment_id=action.comment_id,
        status=action.status,
        error_message=action.error_message,
        sent_at=action.sent_at,
        content=action.content,
    )


def _map_douyin_personal_reply_action(action: DouyinPersonalReplyAction) -> PlatformReplyActionOut:
    return PlatformReplyActionOut(
        id=action.id,
        created_at=action.created_at,
        updated_at=action.updated_at,
        platform="douyin",
        integration_type="personal",
        tenant_id=action.tenant_id,
        account_id=action.account_id,
        comment_id=action.comment_id,
        status=action.status,
        error_message=action.error_message,
        sent_at=action.sent_at,
        content=action.content,
    )


def list_reply_actions(
    db: Session,
    tenant_id: str,
    *,
    platform: Optional[str] = None,
    integration_type: Optional[str] = None,
    status: Optional[str] = None,
    account_id: Optional[str] = None,
) -> list[PlatformReplyActionOut]:
    items: list[PlatformReplyActionOut] = []
    if platform in (None, "all", "bilibili"):
        rows = db.scalars(select(ReplyAction).where(ReplyAction.tenant_id == tenant_id)).all()
        for row in rows:
            if status and row.status != status:
                continue
            if account_id and row.account_id != account_id:
                continue
            items.append(_map_bilibili_reply_action(row))
    if platform in (None, "all", "douyin"):
        if integration_type in (None, "all", "enterprise"):
            rows = db.scalars(select(DouyinReplyAction).where(DouyinReplyAction.tenant_id == tenant_id)).all()
            for row in rows:
                if status and row.status != status:
                    continue
                if account_id and row.account_id != account_id:
                    continue
                items.append(_map_douyin_reply_action(row))
        if integration_type in (None, "all", "personal"):
            rows = db.scalars(
                select(DouyinPersonalReplyAction).where(DouyinPersonalReplyAction.tenant_id == tenant_id)
            ).all()
            for row in rows:
                if status and row.status != status:
                    continue
                if account_id and row.account_id != account_id:
                    continue
                items.append(_map_douyin_personal_reply_action(row))
    return sorted(items, key=lambda item: item.created_at, reverse=True)


def _resolve_douyin_comment_kind(
    db: Session,
    tenant_id: str,
    comment_id: str,
    integration_type: Optional[str],
) -> str:
    if integration_type in ("enterprise", "personal"):
        return integration_type
    enterprise = db.get(DouyinComment, comment_id)
    if enterprise is not None and enterprise.tenant_id == tenant_id:
        return "enterprise"
    personal = db.get(DouyinPersonalComment, comment_id)
    if personal is not None and personal.tenant_id == tenant_id:
        return "personal"
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")


def get_comment_detail(
    db: Session,
    tenant_id: str,
    platform: str,
    comment_id: str,
    integration_type: Optional[str] = None,
) -> PlatformCommentDetailOut:
    if platform == "bilibili":
        detail = comment_service.get_comment_detail(db, tenant_id, comment_id)
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        comment = _map_bilibili_comment(detail["comment"])
        drafts = [
            PlatformReplyDraftOut(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                content=item.content,
                status=item.status,
            )
            for item in detail["reply_drafts"]
        ]
        actions = [_map_bilibili_reply_action(item) for item in detail["reply_actions"]]
        events = [
            PlatformCommentEventOut(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                event_type=item.event_type,
                payload=item.payload,
            )
            for item in detail["events"]
        ]
        return PlatformCommentDetailOut(**comment.model_dump(), events=events, reply_drafts=drafts, reply_actions=actions)

    if platform == "douyin":
        resolved = _resolve_douyin_comment_kind(db, tenant_id, comment_id, integration_type)
        if resolved == "enterprise":
            comment = db.get(DouyinComment, comment_id)
            if comment is None or comment.tenant_id != tenant_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
            mapped = _map_douyin_comment(comment)
            actions = list_reply_actions(db, tenant_id, platform="douyin", integration_type="enterprise")
            comment_actions = [item for item in actions if item.comment_id == comment.id]
            return PlatformCommentDetailOut(
                **mapped.model_dump(),
                events=[],
                reply_drafts=[],
                reply_actions=comment_actions,
            )
        comment = db.get(DouyinPersonalComment, comment_id)
        if comment is None or comment.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        mapped = _map_douyin_personal_comment(comment)
        actions = list_reply_actions(db, tenant_id, platform="douyin", integration_type="personal")
        comment_actions = [item for item in actions if item.comment_id == comment.id]
        return PlatformCommentDetailOut(
            **mapped.model_dump(),
            events=[],
            reply_drafts=[],
            reply_actions=comment_actions,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported platform")


def mark_comments_handled(db: Session, tenant_id: str, items: list[dict], is_handled: bool, user) -> int:
    bilibili_ids = [item["id"] for item in items if item["platform"] == "bilibili"]
    douyin_enterprise_ids = [
        item["id"]
        for item in items
        if item["platform"] == "douyin" and item.get("integration_type") != "personal"
    ]
    douyin_personal_ids = [
        item["id"]
        for item in items
        if item["platform"] == "douyin" and item.get("integration_type") == "personal"
    ]

    unresolved = [
        item
        for item in items
        if item["platform"] == "douyin" and item.get("integration_type") in (None, "", "all")
    ]
    for item in unresolved:
        kind = _resolve_douyin_comment_kind(db, tenant_id, item["id"], None)
        if kind == "personal":
            if item["id"] not in douyin_personal_ids:
                douyin_personal_ids.append(item["id"])
            if item["id"] in douyin_enterprise_ids:
                douyin_enterprise_ids.remove(item["id"])
        else:
            if item["id"] not in douyin_enterprise_ids:
                douyin_enterprise_ids.append(item["id"])

    updated = 0
    if bilibili_ids:
        updated += comment_service.mark_comments_handled(db, tenant_id, bilibili_ids, is_handled, user)
    if douyin_enterprise_ids:
        updated += douyin_service.mark_comments_handled(db, tenant_id, douyin_enterprise_ids, is_handled, user)
    if douyin_personal_ids:
        updated += douyin_personal_service.mark_comments_handled(db, tenant_id, douyin_personal_ids, is_handled, user)
    return updated


async def generate_reply_suggestion(
    db: Session,
    tenant_id: str,
    *,
    platform: str,
    comment_id: str,
    account_id: str,
    integration_type: Optional[str] = None,
    extra_instruction: Optional[str],
    user,
) -> tuple[str, bool]:
    detail = get_comment_detail(db, tenant_id, platform, comment_id, integration_type=integration_type)
    target = None
    if detail.platform == "bilibili":
        target = db.get(MonitorTarget, detail.target_id)
    elif detail.integration_type == "enterprise":
        target = db.get(DouyinTarget, detail.target_id)
    elif detail.integration_type == "personal":
        target = db.get(DouyinPersonalTarget, detail.target_id)
    content = await ai_reply_service.generate_reply_suggestion(
        platform=detail.platform,
        author_name=detail.author_name,
        content=detail.content,
        target_title=target.title if target else None,
        parent_content=None,
        extra_instruction=extra_instruction,
    )
    log_audit(
        db,
        "ai.reply.generate",
        "reply_draft",
        tenant_id=tenant_id,
        user=user,
        payload={
            "platform": platform,
            "integration_type": detail.integration_type,
            "comment_id": comment_id,
            "content_length": len(content),
        },
    )
    db.commit()
    mode = ai_reply_service.get_tenant_ai_reply_mode(db, tenant_id)
    if mode == "direct_send":
        payload = PlatformReplySendRequest(
            platform=platform,
            integration_type=detail.integration_type,
            comment_id=comment_id,
            account_id=account_id,
            content=content,
        )
        await send_reply(db, tenant_id, payload, user)
        return content, True
    return content, False


async def send_reply(db: Session, tenant_id: str, payload: PlatformReplySendRequest, user) -> PlatformReplyActionOut:
    if payload.platform == "bilibili":
        action = await reply_service.send_reply(
            db,
            tenant_id=tenant_id,
            account_id=payload.account_id,
            comment_id=payload.comment_id,
            content=payload.content,
            draft_id=payload.draft_id,
            user=user,
        )
        return _map_bilibili_reply_action(action)
    if payload.platform == "douyin":
        if not payload.content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reply content required")
        resolved = _resolve_douyin_comment_kind(db, tenant_id, payload.comment_id, payload.integration_type)
        if resolved == "personal":
            action = await douyin_personal_service.gateway.reply_to_comment(
                db,
                tenant_id=tenant_id,
                account_id=payload.account_id,
                comment_id=payload.comment_id,
                content=payload.content,
                user=user,
            )
            return _map_douyin_personal_reply_action(action)
        action = await douyin_service.gateway.reply_to_comment(
            db,
            tenant_id=tenant_id,
            account_id=payload.account_id,
            comment_id=payload.comment_id,
            content=payload.content,
            user=user,
        )
        return _map_douyin_reply_action(action)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported platform")
