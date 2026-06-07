from __future__ import annotations

import json
from typing import Any, Dict

from cryptography.fernet import Fernet

from app.core.config import settings

fernet = Fernet(settings.fernet_key.encode("utf-8"))


def encrypt_payload(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return fernet.encrypt(raw).decode("utf-8")


def decrypt_payload(token: str) -> Dict[str, Any]:
    raw = fernet.decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))

