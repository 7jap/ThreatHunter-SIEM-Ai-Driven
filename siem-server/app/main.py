from fastapi import FastAPI
import uvicorn
import logging
import asyncio
from contextlib import asynccontextmanager

from app.database.session import init_db
from app.ai.worker import ai_worker_loop
from app.api.agents import router as agents_router
from app.api.events import router as events_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("siem_server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting SIEM Server Initialization...")
    
    # Initialize DB (create tables if they don't exist)
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")
    
    # Start background AI worker
    worker_task = asyncio.create_task(ai_worker_loop())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Server...")
    worker_task.cancel()

from app.api.auth import router as auth_router
from app.api.ws import router as ws_router
from app.api.alerts import router as alerts_router
from app.api.system import router as system_router
from app.api.users import router as users_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SIEM Central Server", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since dashboard is decoupled, allow all or configure via env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(agents_router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(events_router, prefix="/api/v1", tags=["Events"])
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(system_router, prefix="/api/v1/system", tags=["System"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
from app.api.chat import router as chat_router
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(ws_router, tags=["WebSocket"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    # Force cleartext HTTP mode for React Dashboard compatibility
    logger.info("Starting SIEM Server in HTTP cleartext mode...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8443, reload=True)
