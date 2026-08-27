"""
Minimal WebSocket connection manager used to push live updates to every
connected browser tab (public map, volunteer dashboard, control room).

Messages are standardized JSON envelopes:
{"event": "<event-name>", "data": {...}, "timestamp": "<ISO-8601>"}.
Routers and the hardware simulator call `manager.broadcast(...)` after any
DB write that other screens care about.
"""
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("navix.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event: str, data: Any) -> None:
        envelope = {"event": event, "data": data, "timestamp": datetime.utcnow().isoformat()}
        message = json.dumps(envelope, default=str)
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)

    def connection_count(self) -> int:
        return len(self.active_connections)


# Single shared instance imported across routers/services/simulator.
manager = ConnectionManager()
