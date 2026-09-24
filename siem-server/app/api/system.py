from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Dict, Any
from pydantic import BaseModel

from app.database.session import get_db
from app.database.models.system import SystemSetting, AuditLog
from app.api.deps import RequirePermissions
from app.core.permissions import Permissions

router = APIRouter()

class SettingUpdate(BaseModel):
    value: Any

@router.get("/settings", dependencies=[Depends(RequirePermissions([Permissions.SYSTEM_VIEW]))])
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}

@router.put("/settings/{key}", dependencies=[Depends(RequirePermissions([Permissions.SYSTEM_CONFIGURE]))])
async def update_setting(key: str, req: SettingUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalars().first()
    
    if not setting:
        setting = SystemSetting(key=key, value=req.value)
        db.add(setting)
    else:
        setting.value = req.value
        
    await db.commit()
    return {"status": "success", "key": key, "value": req.value}

@router.get("/audit", dependencies=[Depends(RequirePermissions([Permissions.AUDIT_VIEW]))])
async def get_audit_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit))
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "user_id": l.user_id,
            "target_type": l.target_type,
            "timestamp": l.timestamp
        } for l in logs
    ]

from app.database.models.ai import AIProvider

class AIProviderCreate(BaseModel):
    name: str
    endpoint: str | None = None
    model: str | None = None
    api_key: str | None = None
    is_enabled: bool = False
    is_default: bool = False

@router.get("/ai-providers", dependencies=[Depends(RequirePermissions([Permissions.SYSTEM_VIEW]))])
async def get_ai_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProvider))
    providers = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "endpoint": p.endpoint,
            "model": p.model,
            "is_enabled": p.is_enabled,
            "is_default": p.is_default,
            "has_api_key": bool(p.api_key_encrypted)
        } for p in providers
    ]

@router.post("/ai-providers", dependencies=[Depends(RequirePermissions([Permissions.SYSTEM_CONFIGURE]))])
async def create_ai_provider(req: AIProviderCreate, db: AsyncSession = Depends(get_db)):
    if req.is_default:
        old_defaults = (await db.execute(select(AIProvider).where(AIProvider.is_default == True))).scalars().all()
        for od in old_defaults:
            od.is_default = False

    provider = AIProvider(
        name=req.name,
        endpoint=req.endpoint,
        model=req.model,
        is_enabled=req.is_enabled,
        is_default=req.is_default
    )
    if req.api_key:
        provider.api_key_encrypted = req.api_key
        
    db.add(provider)
    await db.commit()
    return {"status": "success", "id": provider.id}

@router.put("/ai-providers/{provider_id}", dependencies=[Depends(RequirePermissions([Permissions.SYSTEM_CONFIGURE]))])
async def update_ai_provider(provider_id: str, req: AIProviderCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    if req.is_default:
        old_defaults = (await db.execute(select(AIProvider).where(AIProvider.is_default == True))).scalars().all()
        for od in old_defaults:
            if od.id != provider_id:
                od.is_default = False

    provider.name = req.name
    provider.endpoint = req.endpoint
    provider.model = req.model
    if req.api_key and req.api_key.strip() != "":
        provider.api_key_encrypted = req.api_key
    provider.is_enabled = req.is_enabled
    provider.is_default = req.is_default
    
    await db.commit()
    return {"status": "success", "id": provider.id}

@router.delete("/ai-providers/{provider_id}", dependencies=[Depends(RequirePermissions([Permissions.SYSTEM_CONFIGURE]))])
async def delete_ai_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    await db.delete(provider)
    await db.commit()
    return {"status": "success"}
