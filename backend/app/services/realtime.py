from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket

from app.core.metrics import WEBSOCKET_CONNECTIONS


class WebSocketManager:
    def __init__(self) -> None:
        self.connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, tenant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.connections[tenant_id].add(websocket)
        WEBSOCKET_CONNECTIONS.inc()

    async def disconnect(self, tenant_id: str, websocket: WebSocket) -> None:
        async with self.lock:
            self.connections[tenant_id].discard(websocket)
            if not self.connections[tenant_id]:
                self.connections.pop(tenant_id, None)
        WEBSOCKET_CONNECTIONS.dec()

    async def broadcast(self, tenant_id: str, event: str, payload: dict) -> None:
        message = json.dumps({"event": event, "payload": payload}, ensure_ascii=False)
        async with self.lock:
            targets = list(self.connections.get(tenant_id, set()))
        for websocket in targets:
            try:
                await websocket.send_text(message)
            except Exception:
                await self.disconnect(tenant_id, websocket)


manager = WebSocketManager()
