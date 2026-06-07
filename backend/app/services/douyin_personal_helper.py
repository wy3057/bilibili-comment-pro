from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class DouyinPersonalHelperClient:
    def __init__(self) -> None:
        self.base_url = settings.douyin_personal_helper_base_url.rstrip("/")

    def _ensure_enabled(self) -> None:
        if not settings.douyin_personal_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Douyin personal helper is disabled",
            )

    async def _request(self, method: str, path: str, json_body: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        self._ensure_enabled()
        async with httpx.AsyncClient(timeout=settings.douyin_personal_request_timeout_seconds) as client:
            response = await client.request(method, f"{self.base_url}{path}", json=json_body)
        try:
            payload = response.json()
        except ValueError:
            payload = {"detail": response.text}
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(
                    payload.get("detail")
                    if isinstance(payload, dict)
                    else response.text or "Douyin personal helper request failed"
                ),
            )
        if isinstance(payload, dict) and not payload.get("ok", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(payload.get("detail") or payload.get("error") or "Douyin personal helper request failed"),
            )
        return payload if isinstance(payload, dict) else {"data": payload}

    async def start_login_session(self) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/sessions/start",
            {"headless": settings.douyin_personal_browser_headless},
        )

    async def get_login_session(self, helper_session_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/sessions/{helper_session_id}")

    async def normalize_cookie(self, cookie: str) -> dict[str, Any]:
        return await self._request("POST", "/runtime/normalize", {"cookie": cookie})

    async def refresh_runtime(self, cookie: str, runtime: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/runtime/refresh", {"cookie": cookie, "runtime": runtime})

    async def resolve_target(
        self,
        *,
        cookie: str,
        runtime: dict[str, Any],
        aweme_id: Optional[str] = None,
        video_url: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/targets/resolve",
            {
                "cookie": cookie,
                "runtime": runtime,
                "aweme_id": aweme_id,
                "video_url": video_url,
                "title": title,
            },
        )

    async def fetch_comments(self, *, cookie: str, runtime: dict[str, Any], aweme_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/comments/fetch",
            {"cookie": cookie, "runtime": runtime, "aweme_id": aweme_id},
        )

    async def reply_comment(
        self,
        *,
        cookie: str,
        runtime: dict[str, Any],
        aweme_id: str,
        comment_id: str,
        comment_text: Optional[str] = None,
        comment_author: Optional[str] = None,
        content: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/comments/reply",
            {
                "cookie": cookie,
                "runtime": runtime,
                "aweme_id": aweme_id,
                "comment_id": comment_id,
                "comment_text": comment_text,
                "comment_author": comment_author,
                "content": content,
            },
        )


helper_client = DouyinPersonalHelperClient()
