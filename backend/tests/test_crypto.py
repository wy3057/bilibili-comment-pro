from __future__ import annotations

from app.core.crypto import decrypt_payload, encrypt_payload


def test_encrypt_decrypt_payload_roundtrip() -> None:
    payload = {
        "sessdata": "sess",
        "bili_jct": "csrf",
        "nested": {"k": "v"},
        "count": 3,
    }
    encrypted = encrypt_payload(payload)
    assert encrypted != "sess"
    decrypted = decrypt_payload(encrypted)
    assert decrypted == payload

