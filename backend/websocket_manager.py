"""
Minimal WebSocket connection manager used to push live updates to every
connected browser tab (public map, volunteer dashboard, control room).

Messages are small JSON envelopes: {"event": "<event-name>", "data": {...}}.
Routers and the hardware simulator call `manager.broadcast(...)` after any
DB write that other screens care about.
"""
import json
import logging
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
        message = json.dumps({"event": event, "data": data}, default=str)
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


# Single shared instance imported across routers/services/simulator.
manager = ConnectionManager()
