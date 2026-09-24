from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from app.database.session import get_db
from app.database.models.events import Alert, AlertAIAnalysis
from app.api.deps import RequirePermissions, get_current_user
from app.core.permissions import Permissions

router = APIRouter()

@router.get("/", dependencies=[Depends(RequirePermissions([Permissions.ALERTS_VIEW]))])
async def get_alerts(
    limit: int = 100, 
    status: str = None,
    severity: int = None,
    search: str = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert).order_by(desc(Alert.timestamp))
    
    if status and status != 'all':
        query = query.where(Alert.status == status)
    if severity and str(severity) != 'all':
        query = query.where(Alert.severity == int(severity))
    if search:
        query = query.where(
            (Alert.signature.ilike(f"%{search}%")) |
            (Alert.source_ip.ilike(f"%{search}%")) |
            (Alert.destination_ip.ilike(f"%{search}%"))
        )
        
    result = await db.execute(query.limit(limit))
    alerts = result.scalars().all()
    
    output = []
    for a in alerts:
        output.append({
            "id": a.id,
            "timestamp": a.timestamp,
            "severity": a.severity,
            "signature": a.signature,
            "category": a.category,
            "source_ip": a.source_ip,
            "destination_ip": a.destination_ip,
            "status": a.status
        })
    
    alert_ids = [a["id"] for a in output]
    if alert_ids:
        ai_res = await db.execute(select(AlertAIAnalysis).where(AlertAIAnalysis.alert_id.in_(alert_ids)))
        analyses = ai_res.scalars().all()
        verdict_map = {an.alert_id: {"verdict": an.summary, "confidence": an.confidence} for an in analyses}
        for a in output:
            if a["id"] in verdict_map:
                a["ai_verdict"] = verdict_map[a["id"]]["verdict"]
                a["ai_confidence"] = verdict_map[a["id"]]["confidence"]
                
    return output

@router.get("/stats", dependencies=[Depends(RequirePermissions([Permissions.ALERTS_VIEW]))])
async def get_alerts_stats(db: AsyncSession = Depends(get_db)):
    total_result = await db.execute(select(func.count(Alert.id)))
    total_alerts = total_result.scalar() or 0
    
    sev_result = await db.execute(select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity))
    by_severity = {str(row[0]): row[1] for row in sev_result.all()}
    
    # Generate timeline for the last 24 hours (grouped by hour)
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(hours=24)
    
    # SQLite friendly hourly grouping
    # strftime('%Y-%m-%d %H:00', timestamp)
    timeline_query = select(
        func.strftime('%Y-%m-%d %H:00', Alert.timestamp).label("hour"),
        func.count(Alert.id)
    ).where(Alert.timestamp >= one_day_ago).group_by("hour").order_by("hour")
    
    timeline_result = await db.execute(timeline_query)
    timeline_data = [{"time": row[0], "alerts": row[1]} for row in timeline_result.all()]
    
    return {
        "total_alerts": total_alerts,
        "by_severity": by_severity,
        "timeline": timeline_data
    }

@router.get("/{alert_id}", dependencies=[Depends(RequirePermissions([Permissions.ALERTS_VIEW]))])
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    from app.database.models.events import Event
    
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    event_result = await db.execute(select(Event).where(Event.id == alert.event_id))
    event = event_result.scalars().first()
    raw_payload = event.payload if event else None

    ai_result = await db.execute(select(AlertAIAnalysis).where(AlertAIAnalysis.alert_id == alert_id))
    ai_analysis = ai_result.scalars().first()
    
    data = {
        "id": alert.id,
        "timestamp": alert.timestamp,
        "severity": alert.severity,
        "signature": alert.signature,
        "category": alert.category,
        "source_ip": alert.source_ip,
        "destination_ip": alert.destination_ip,
        "source_port": alert.source_port,
        "destination_port": alert.destination_port,
        "protocol": alert.protocol,
        "status": alert.status,
        "raw_payload": raw_payload,
        "ai_analysis": None
    }
    
    if ai_analysis:
        data["ai_analysis"] = {
            "verdict": ai_analysis.summary,
            "confidence": ai_analysis.confidence,
            "explanation": ai_analysis.explanation,
            "recommended_actions": ai_analysis.recommended_investigation
        }
        
    return data

class UpdateAlertStatusReq(BaseModel):
    status: str

@router.put("/{alert_id}/status", dependencies=[Depends(RequirePermissions([Permissions.ALERTS_INVESTIGATE]))])
async def update_alert_status(alert_id: str, payload: UpdateAlertStatusReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    alert.status = payload.status
    await db.commit()
    return {"status": "success"}
