from fastapi import FastAPI
import uvicorn
import logging
from contextlib import asynccontextmanager

from database.session import init_db
from api.agents import router as agents_router
from api.events import router as events_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("siem_server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")
    yield
    # Shutdown
    logger.info("Shutting down Server...")

app = FastAPI(title="SIEM Central Server", version="1.0.0", lifespan=lifespan)

app.include_router(agents_router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(events_router, prefix="/api/v1", tags=["Events"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import os
    import ssl
    cert_path = os.environ.get("SIEM_SERVER_CERTS", "../test_env/certs")
    
    ssl_keyfile = os.path.join(cert_path, "server.key")
    ssl_certfile = os.path.join(cert_path, "server.crt")
    ssl_ca_certs = os.path.join(cert_path, "ca.crt")
    
    if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        logger.info("Starting with TLS and mTLS enabled...")
        uvicorn.run("main:app", host="0.0.0.0", port=8443, reload=True, 
                    ssl_keyfile=ssl_keyfile, 
                    ssl_certfile=ssl_certfile,
                    ssl_ca_certs=ssl_ca_certs,
                    ssl_cert_reqs=ssl.CERT_REQUIRED)
    else:
        logger.warning("TLS certs not found! Starting in cleartext mode...")
        uvicorn.run("main:app", host="0.0.0.0", port=8443, reload=True)
