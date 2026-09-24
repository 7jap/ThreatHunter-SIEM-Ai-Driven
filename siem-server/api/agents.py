from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from pydantic import BaseModel
from database.session import get_db
from database.models import Agent

router = APIRouter()

class RegistrationRequest(BaseModel):
    agent_id: str
    hostname: str

class HeartbeatRequest(BaseModel):
    agent_id: str
    timestamp: str
    status: dict

def get_agent_id(x_agent_id: str = Header(..., alias="X-Agent-ID")):
    if not x_agent_id:
        raise HTTPException(status_code=401, detail="Missing X-Agent-ID Header")
    return x_agent_id

import logging
logger = logging.getLogger("siem_server.agents")

@router.post("/register")
async def register_agent(req: RegistrationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    existing = result.scalars().first()
    
    if existing:
        return {"status": "already_registered", "agent_id": existing.id, "state": existing.status}
        
    logger.warning(f"SECURITY ALERT: New Agent Request Received! Agent ID: {req.agent_id}, Hostname: {req.hostname}")
    
    new_agent = Agent(
        id=req.agent_id,
        hostname=req.hostname,
        status="PENDING" # Requires admin approval
    )
    db.add(new_agent)
    await db.commit()
    
    return {"status": "registered_pending_approval", "agent_id": new_agent.id}

@router.post("/heartbeat")
async def heartbeat(
    req: HeartbeatRequest,
    agent_id: str = Depends(get_agent_id),
    db: AsyncSession = Depends(get_db)
):
    if req.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Agent ID mismatch")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if agent.status != "ACTIVE":
        raise HTTPException(status_code=403, detail=f"Agent is not ACTIVE (Current status: {agent.status})")
        
    # Update heartbeat stats
    agent.last_heartbeat = datetime.now(timezone.utc)
    agent.suricata_version = req.status.get("suricata_version")
    agent.agent_version = req.status.get("agent_version")
    
    await db.commit()
    
    return {"status": "ack"}
