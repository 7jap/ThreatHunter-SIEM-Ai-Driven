from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timezone
import dateutil.parser

from app.database.session import get_db
from app.database.models.agents import Agent
from app.database.models.events import Event, Alert
from app.database.models.ai import AIJob

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

    # 1. Validate agent identity and approval status
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalars().first()
    
    if not agent or agent.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Agent invalid or revoked")
        
    acked_ids = []
    
    for payload in req.events:
        evt_id = payload.get("_event_id")
        ts_str = payload.get("timestamp")
        event_type = payload.get("event_type")
        
        if not evt_id or not ts_str:
            continue # Malformed event, skip
            
        # SERVER-SIDE FILTERING: Only process alerts
        if event_type != "alert":
            acked_ids.append(evt_id)
            continue
            
        # Parse timestamp safely
        try:
            ts_parsed = dateutil.parser.parse(ts_str)
        except Exception:
            ts_parsed = datetime.now(timezone.utc)

        # 2. Store Raw Event
        new_event = Event(
            event_id=evt_id,
            agent_id=agent_id,
            timestamp=ts_str,
            event_type=event_type,
            source="suricata",
            payload=payload
        )
        db.add(new_event)
        
        try:
            await db.flush() # Flush to get new_event.id
            
            # 3. Normalize and Store Alert
            alert_data = payload.get("alert", {})
            new_alert = Alert(
                event_id=new_event.id,
                agent_id=agent_id,
                timestamp=ts_parsed,
                severity=alert_data.get("severity"),
                signature=alert_data.get("signature"),
                category=alert_data.get("category"),
                source_ip=payload.get("src_ip"),
                source_port=payload.get("src_port"),
                destination_ip=payload.get("dest_ip"),
                destination_port=payload.get("dest_port"),
                protocol=payload.get("proto"),
                status="NEW"
            )
            db.add(new_alert)
            await db.flush() # Flush to get new_alert.id
            
            # 4. Queue AI Analysis Job (Asynchronous execution handled by separate worker)
            priority = "MEDIUM"
            if new_alert.severity in [1, 2]: # Assuming 1 is high in Suricata
                priority = "HIGH"
                
            new_ai_job = AIJob(
                alert_id=new_alert.id,
                priority=priority,
                status="PENDING"
            )
            db.add(new_ai_job)
            
            # 5. Commit Transaction (DB First Guarantee)
            await db.commit()
            acked_ids.append(evt_id)
            
            # 6. Broadcast Real-time Event
            # Using asyncio.create_task to not block the ingestion response
            import asyncio
            from app.websocket.manager import manager
            
            alert_payload = {
                "id": new_alert.id,
                "severity": new_alert.severity,
                "signature": new_alert.signature,
                "source_ip": new_alert.source_ip,
                "destination_ip": new_alert.destination_ip,
                "agent_id": new_alert.agent_id,
                "status": new_alert.status,
                "timestamp": new_alert.timestamp.isoformat() if new_alert.timestamp else None
            }
            asyncio.create_task(manager.broadcast("alert.created", alert_payload))
            
        except IntegrityError:
            # Duplicate event_id, ack it safely
            await db.rollback()
            acked_ids.append(evt_id)
        except Exception as e:
            await db.rollback()
            # Do not ack if real DB failure, agent will retry
            import logging
            logging.error(f"Failed to ingest event {evt_id}: {str(e)}")
            
    # Return success to agent BEFORE AI analysis starts
    return {"status": "success", "acked_event_ids": acked_ids}
