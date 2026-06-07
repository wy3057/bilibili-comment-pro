from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.entities import AIReplyMode, TenantAISetting


PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
    "deepseek": "https://api.deepseek.com",
}


def _provider() -> str:
    return settings.ai_reply_provider.strip().lower() or "openai"


def _base_url() -> str:
    if settings.ai_reply_base_url.strip():
        return settings.ai_reply_base_url.strip()
    return PROVIDER_BASE_URLS.get(_provider(), PROVIDER_BASE_URLS["openai"])


def is_ai_reply_enabled() -> bool:
    return bool(settings.ai_reply_enabled and settings.ai_reply_api_key and settings.ai_reply_model)


def get_tenant_ai_reply_mode(db, tenant_id: str) -> str:
    row = db.query(TenantAISetting).filter(TenantAISetting.tenant_id == tenant_id).one_or_none()
    return row.ai_reply_mode if row is not None else AIReplyMode.manual_review.value


def update_tenant_ai_reply_mode(db, tenant_id: str, mode: str) -> str:
    allowed = {AIReplyMode.manual_review.value, AIReplyMode.direct_send.value}
    if mode not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported AI reply mode")
    row = db.query(TenantAISetting).filter(TenantAISetting.tenant_id == tenant_id).one_or_none()
    if row is None:
        row = TenantAISetting(tenant_id=tenant_id, ai_reply_mode=mode)
        db.add(row)
    else:
        row.ai_reply_mode = mode
        db.add(row)
    db.commit()
    db.refresh(row)
    return row.ai_reply_mode


def get_ai_reply_status(db=None, tenant_id: Optional[str] = None) -> dict:
    return {
        "enabled": is_ai_reply_enabled(),
        "provider": _provider(),
        "model": settings.ai_reply_model,
        "base_url": _base_url(),
        "api_mode": settings.ai_reply_api_mode,
        "mode": get_tenant_ai_reply_mode(db, tenant_id) if db is not None and tenant_id is not None else AIReplyMode.manual_review.value,
    }


def _client() -> AsyncOpenAI:
    if not is_ai_reply_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI reply not configured")
    return AsyncOpenAI(
        api_key=settings.ai_reply_api_key,
        base_url=_base_url(),
        timeout=settings.ai_reply_timeout_seconds,
    )


def _build_user_prompt(
    *,
    platform: str,
    author_name: str,
    content: str,
    target_title: Optional[str],
    parent_content: Optional[str],
    extra_instruction: Optional[str],
) -> str:
    parts = [
        f"平台：{platform}",
        f"目标标题：{target_title or '未知'}",
        f"评论用户：{author_name}",
        f"评论内容：{content}",
    ]
    if parent_content:
        parts.append(f"上文/父评论：{parent_content}")
    if extra_instruction:
        parts.append(f"额外要求：{extra_instruction}")
    parts.append("请生成一条适合直接回复的中文正文，控制在 80 字以内。")
    return "\n".join(parts)


async def generate_reply_suggestion(
    *,
    platform: str,
    author_name: str,
    content: str,
    target_title: Optional[str] = None,
    parent_content: Optional[str] = None,
    extra_instruction: Optional[str] = None,
) -> str:
    client = _client()
    user_prompt = _build_user_prompt(
        platform=platform,
        author_name=author_name,
        content=content,
        target_title=target_title,
        parent_content=parent_content,
        extra_instruction=extra_instruction,
    )

    if settings.ai_reply_api_mode == "responses":
        response = await client.responses.create(
            model=settings.ai_reply_model,
            temperature=settings.ai_reply_temperature,
            max_output_tokens=settings.ai_reply_max_tokens,
            input=[
                {"role": "system", "content": settings.ai_reply_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = getattr(response, "output_text", "").strip()
    else:
        response = await client.chat.completions.create(
            model=settings.ai_reply_model,
            temperature=settings.ai_reply_temperature,
            max_tokens=settings.ai_reply_max_tokens,
            messages=[
                {"role": "system", "content": settings.ai_reply_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = (response.choices[0].message.content or "").strip()

    if not text:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI reply returned empty content")
    return text
