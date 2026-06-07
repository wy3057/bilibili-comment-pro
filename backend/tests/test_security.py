from __future__ import annotations

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    sha256_text,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    password = "ChangeMe123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip() -> None:
    token, expires_at = create_refresh_token("user-456")
    payload = decode_refresh_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"
    assert expires_at.isoformat()


def test_sha256_text_stable() -> None:
    assert sha256_text("abc") == sha256_text("abc")
    assert sha256_text("abc") != sha256_text("abcd")

