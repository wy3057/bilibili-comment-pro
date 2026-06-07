from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _derive_fernet_key(raw: str) -> str:
    if len(raw) == 44:
        return raw
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Bilibili Comment Platform"
    env: str = "development"
    api_prefix: str = "/api"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/bilibili_comment"
    )
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-access-secret-at-least-32-bytes"
    jwt_refresh_secret: str = "change-me-refresh-secret-at-least-32"
    token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    credential_cipher_key: str = "change-me-credential-cipher-key"
    bootstrap_owner_email: str = "owner@example.com"
    bootstrap_owner_password: str = "ChangeMe123!"
    bootstrap_owner_name: str = "Platform Owner"
    bootstrap_tenant_name: str = "Default Tenant"
    bootstrap_tenant_slug: str = "default"
    frontend_origin: str = "http://localhost:4173"
    public_api_base_url: str = "http://localhost:8000"
    public_web_base_url: str = "http://localhost:4173"
    douyin_oauth_scopes: str = "user_info,item.comment,video.data"
    douyin_oauth_state_ttl_seconds: int = 600
    douyin_personal_enabled: bool = False
    douyin_personal_helper_base_url: str = "http://douyin-personal-helper:4300"
    douyin_personal_login_session_ttl_seconds: int = 600
    douyin_personal_request_timeout_seconds: int = 30
    douyin_personal_browser_headless: bool = True
    ai_reply_enabled: bool = False
    ai_reply_provider: str = "openai"
    ai_reply_api_key: str = ""
    ai_reply_base_url: str = ""
    ai_reply_model: str = "gpt-4.1-mini"
    ai_reply_api_mode: str = "chat_completions"
    ai_reply_temperature: float = 0.7
    ai_reply_max_tokens: int = 300
    ai_reply_timeout_seconds: int = 30
    ai_reply_system_prompt: str = (
        "你是一个中文客服与社区运营助手。你的任务是基于用户评论，生成一条简洁、礼貌、自然、"
        "不夸张、不机械的人工回复建议。除非评论本身要求，否则不要承诺无法确认的事实，不要编造信息。"
        "输出只包含最终回复正文，不要解释。"
    )
    metrics_enabled: bool = True

    @property
    def fernet_key(self) -> str:
        return _derive_fernet_key(self.credential_cipher_key)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
