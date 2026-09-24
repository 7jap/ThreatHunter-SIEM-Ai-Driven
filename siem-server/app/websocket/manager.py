from fastapi import WebSocket
from typing import List
import json
import logging

logger = logging.getLogger("siem_server.websocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict):
        if not self.active_connections:
            return
            
        # Optional: Add datetime serialization fallback here if needed
        def datetime_handler(x):
            if hasattr(x, "isoformat"):
                return x.isoformat()
            raise TypeError("Unknown type")
            
        message = json.dumps({"event": event_type, "data": data}, default=datetime_handler)
        
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send WS message: {e}")
                dead_connections.append(connection)
                
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()
