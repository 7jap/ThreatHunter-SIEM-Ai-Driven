import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import AsyncSessionLocal
from app.database.models.users import User, Role
from app.core.security import get_password_hash
from sqlalchemy.future import select

async def main():
    async with AsyncSessionLocal() as db:
        role_result = await db.execute(select(Role).where(Role.name == "Admin"))
        admin_role = role_result.scalars().first()
        if not admin_role:
            admin_role = Role(name="Admin", description="Super Administrator")
            db.add(admin_role)
            await db.flush()

        result = await db.execute(select(User).where(User.username == "testadmin"))
        if not result.scalars().first():
            user = User(
                username="testadmin",
                email="test@example.com",
                password_hash=get_password_hash("password123"),
                display_name="Test Admin"
            )
            user.roles.append(admin_role)
            db.add(user)
            await db.commit()
            print("Test admin created.")
        else:
            print("Test admin already exists.")

if __name__ == "__main__":
    asyncio.run(main())
