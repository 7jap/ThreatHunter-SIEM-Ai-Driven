import asyncio
import logging
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.database.session import AsyncSessionLocal
from app.database.models.ai import AIJob, AIProvider
from app.database.models.events import Alert, AlertAIAnalysis
from app.database.models.system import SystemSetting
from app.ai.gateway import get_ai_provider
from app.websocket.manager import manager

logger = logging.getLogger("siem_server.ai_worker")

async def fetch_context_alerts(db, target_alert, limit=10):
    """Fetch recent alerts from the same source IP for context."""
    result = await db.execute(
        select(Alert)
        .where(Alert.source_ip == target_alert.source_ip)
        .where(Alert.id != target_alert.id)
        .order_by(Alert.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def process_job(job_id: str):
    async with AsyncSessionLocal() as db:
        # Load Job and Alert
        result = await db.execute(select(AIJob).where(AIJob.id == job_id))
        job = result.scalars().first()
        if not job:
            return
            
        result_alert = await db.execute(select(Alert).where(Alert.id == job.alert_id))
        alert = result_alert.scalars().first()
        
        if not alert:
            job.status = "FAILED"
            job.error = "Alert not found"
            await db.commit()
            return
            
        # Update job status
        job.status = "PROCESSING"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        await db.commit()
        
        try:
            # 1. Build Context
            setting_res = await db.execute(select(SystemSetting).where(SystemSetting.key == 'ai_context_size'))
            context_size_setting = setting_res.scalars().first()
            limit = int(context_size_setting.value) if context_size_setting and context_size_setting.value else 10
            
            context_alerts_objs = await fetch_context_alerts(db, alert, limit=limit)
            context_alerts = [{"signature": a.signature, "timestamp": str(a.timestamp)} for a in context_alerts_objs]
            
            alert_data = {
                "id": alert.id,
                "severity": alert.severity,
                "signature": alert.signature,
                "category": alert.category,
                "source_ip": alert.source_ip,
                "destination_ip": alert.destination_ip
            }
            
            # 2. Get AI Providers (Enabled only, Default first)
            providers_res = await db.execute(
                select(AIProvider)
                .where(AIProvider.is_enabled == True)
                .order_by(AIProvider.is_default.desc(), AIProvider.id)
            )
            enabled_providers = providers_res.scalars().all()
            
            if not enabled_providers:
                logger.warning("No active AI Provider found. Falling back to default ollama mock.")
                provider = get_ai_provider("ollama", {})
                analysis_result = await provider.analyze_alert(alert_data, context_alerts)
                provider_name = "ollama"
            else:
                analysis_result = None
                provider_name = None
                last_error = None
                
                # Try providers sequentially (Fallback Mechanism)
                for p in enabled_providers:
                    try:
                        p_config = {
                            "endpoint": p.endpoint,
                            "model": p.model,
                            "api_key": p.api_key_encrypted
                        }
                        provider_instance = get_ai_provider(p.name, p_config)
                        
                        # Set a timeout for the call inside the provider or just await it
                        analysis_result = await provider_instance.analyze_alert(alert_data, context_alerts)
                        
                        # Validate if the analysis_result is an actual valid result or a string error
                        if isinstance(analysis_result, str):
                            # The gateway returned an error string, meaning connection failed
                            raise Exception(analysis_result)
                            
                        provider_name = p.name
                        break # Success! Break the fallback loop
                        
                    except Exception as e:
                        last_error = str(e)
                        logger.warning(f"Provider {p.name} failed: {last_error}. Trying next...")
                        continue
                        
                if not analysis_result or isinstance(analysis_result, str):
                    raise Exception(f"All AI Providers failed. Last error: {last_error}")
            
            # 4. Store Results
            analysis_record = AlertAIAnalysis(
                alert_id=alert.id,
                provider_id=provider_name,
                analysis_status="COMPLETED",
                summary=analysis_result.get("verdict", "UNKNOWN"),
                confidence=float(analysis_result.get("confidence", 0)),
                explanation=analysis_result.get("explanation", ""),
                recommended_investigation=analysis_result.get("recommended_actions", []),
                raw_response=analysis_result.get("raw_response", "")
            )
            db.add(analysis_record)
            
            # Update Alert status
            alert.status = "ANALYZED"
            
            # Update Job status
            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            # 4. Broadcast Notification
            await manager.broadcast("alert.ai_completed", {
                "alert_id": alert.id,
                "verdict": analysis_record.summary,
                "confidence": analysis_record.confidence
            })
            
            logger.info(f"Successfully processed AI Job {job.id} for Alert {alert.id}")
            
        except Exception as e:
            logger.error(f"AI Worker error on job {job.id}: {str(e)}")
            job.status = "FAILED"
            job.error = str(e)
            await db.commit()

async def ai_worker_loop():
    logger.info("AI Worker Loop Started")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AIJob)
                    .where(AIJob.status == "PENDING")
                    .order_by(AIJob.created_at.asc())
                    .limit(5)
                )
                jobs = result.scalars().all()
                
            for job in jobs:
                await process_job(job.id)
                
        except Exception as e:
            logger.error(f"AI Worker loop error: {e}")
            
        await asyncio.sleep(5) # Poll every 5 seconds
