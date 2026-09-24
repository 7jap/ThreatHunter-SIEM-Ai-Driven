from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from pydantic import BaseModel

from app.database.session import get_db
from app.database.models.users import User, Role
from app.core.security import get_password_hash
from app.api.deps import RequirePermissions
from app.core.permissions import Permissions

router = APIRouter()

async def find_role_flexible(db: AsyncSession, name: str):
    if not name:
        return None
    # 1. Exact match
    res = await db.execute(select(Role).where(Role.name == name))
    role = res.scalars().first()
    if role:
        return role
    # 2. Case-insensitive match
    res = await db.execute(select(Role).where(func.lower(Role.name) == name.lower()))
    role = res.scalars().first()
    if role:
        return role
    # 3. Known aliases
    alias_map = {
        "admin": "Admin",
        "administrator": "Admin",
        "analyst": "SOC Analyst",
        "soc analyst": "SOC Analyst",
        "soc": "SOC Analyst",
        "user": "SOC Analyst"
    }
    mapped = alias_map.get(name.lower().strip())
    if mapped:
        res = await db.execute(select(Role).where(Role.name == mapped))
        role = res.scalars().first()
        if role:
            return role
    return None

@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]

class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    email: str
    role_name: str = "Admin"

@router.get("/", dependencies=[Depends(RequirePermissions([Permissions.USERS_VIEW]))])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).options(selectinload(User.roles)))
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "email": u.email,
            "roles": [r.name for r in u.roles],
            "is_active": u.is_active
        } for u in users
    ]

@router.post("/", dependencies=[Depends(RequirePermissions([Permissions.USERS_CREATE]))])
async def create_user(req: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
        
    role = await find_role_flexible(db, req.role_name)
    
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{req.role_name}' not found")
        
    user = User(
        username=req.username,
        email=req.email,
        display_name=req.display_name,
        password_hash=get_password_hash(req.password),
        is_active=True
    )
    user.roles.append(role)
    db.add(user)
    await db.commit()
    
    return {"status": "success", "user_id": user.id}

class UserUpdate(BaseModel):
    display_name: str
    email: str
    role_name: str
    is_active: bool

@router.put("/{user_id}", dependencies=[Depends(RequirePermissions([Permissions.USERS_UPDATE]))])
async def update_user(user_id: str, req: UserUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    role = await find_role_flexible(db, req.role_name)
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{req.role_name}' not found")
        
    user.display_name = req.display_name
    user.email = req.email
    user.is_active = req.is_active
    
    user.roles = [role] # replace roles
    
    await db.commit()
    return {"status": "updated"}

@router.delete("/{user_id}", dependencies=[Depends(RequirePermissions([Permissions.USERS_DELETE]))])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}
