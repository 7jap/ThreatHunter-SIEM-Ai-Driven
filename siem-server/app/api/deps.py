from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import jwt
from jwt.exceptions import PyJWTError

from app.database.session import get_db
from app.core.config import settings
from app.database.models.users import User, Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
        
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if user is None or not user.is_active:
        raise credentials_exception
        
    return user

class RequirePermissions:
    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions
        
    def __call__(self, current_user: User = Depends(get_current_user)):
        # Flatten user permissions from all assigned roles
        user_perms = set()
        for role in current_user.roles:
            for perm in role.permissions:
                user_perms.add(perm.name)
                
        for req in self.required_permissions:
            if req not in user_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Missing required permission '{req}'"
                )
        return current_user
