import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import AsyncSessionLocal
from app.database.models.users import User, Role
from app.core.security import get_password_hash
from sqlalchemy.future import select

async def create():
    async with AsyncSessionLocal() as db:
        role_res = await db.execute(select(Role).where(Role.name == "Admin"))
        admin_role = role_res.scalars().first()
        user_res = await db.execute(select(User).where(User.username == "admin"))
        user = user_res.scalars().first()
        if not user:
            user = User(username="admin", email="admin@localhost", password_hash=get_password_hash("Admin123!"), display_name="SOC Admin")
            if admin_role:
                user.roles.append(admin_role)
            db.add(user)
            await db.commit()
            print("Admin created!")
        else:
            print("Admin already exists.")

if __name__ == "__main__":
    asyncio.run(create())
