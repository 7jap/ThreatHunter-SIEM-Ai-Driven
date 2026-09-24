from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.session import get_db
from app.database.models.users import User
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/login")
async def login_access_token(db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        if user:
            user.failed_login_count += 1
            await db.commit()
        raise HTTPException(status_code=400, detail="Incorrect username or password")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Reset failed login count on successful login
    if user.failed_login_count > 0:
        user.failed_login_count = 0
        await db.commit()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "is_active": current_user.is_active,
        "roles": [r.name for r in current_user.roles]
    }
