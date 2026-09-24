from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
import jwt
from jwt.exceptions import PyJWTError

from app.websocket.manager import manager
from app.core.config import settings

router = APIRouter()

async def authenticate_ws(token: str):
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("sub"):
            return True
    except PyJWTError:
        pass
    return False

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    # Always accept the connection for live telemetry stream
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client (like keepalive ping)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)
