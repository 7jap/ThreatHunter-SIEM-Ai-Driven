from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import List, Dict, Any
from database.session import get_db
from database.models import Agent, Event

router = APIRouter()

class EventBatchRequest(BaseModel):
    agent_id: str
    events: List[Dict[str, Any]]

def get_agent_id(x_agent_id: str = Header(..., alias="X-Agent-ID")):
    if not x_agent_id:
        raise HTTPException(status_code=401, detail="Missing X-Agent-ID Header")
    return x_agent_id

@router.post("/events")
async def ingest_events(
    req: EventBatchRequest,
    agent_id: str = Depends(get_agent_id),
    db: AsyncSession = Depends(get_db)
):
    if req.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Agent ID mismatch")

    # Validate agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    
    if not agent or agent.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Agent invalid or revoked")
        
    acked_ids = []
    
    for payload in req.events:
        evt_id = payload.get("_event_id")
        ts = payload.get("timestamp")
        event_type = payload.get("event_type")
        
        if not evt_id or not ts:
            continue # Malformed event, skip
            
        # SERVER-SIDE FILTERING: Only store alerts, drop everything else but ACK it so Agent deletes it
        if event_type != "alert":
            acked_ids.append(evt_id)
            continue
            
        new_event = Event(
            event_id=evt_id,
            agent_id=agent_id,
            timestamp=ts,
            payload=payload
        )
        
        db.add(new_event)
        
        try:
            await db.commit()
            acked_ids.append(evt_id)
        except IntegrityError:
            # Duplicate event (already received before), still ACK it to remove from client queue
            await db.rollback()
            acked_ids.append(evt_id)
        except Exception as e:
            await db.rollback()
            # Do not append to acked_ids on true failure, agent will retry
            
    return {"status": "success", "acked_event_ids": acked_ids}
