import asyncio
import getpass
import sys
import os

# Ensure the app path is added so we can run this directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import AsyncSessionLocal
from app.database.models.users import User, Role
from app.core.security import get_password_hash
from sqlalchemy.future import select

async def main():
    print("=" * 50)
    print(" SIEM Platform - Admin Initialization ")
    print("=" * 50)
    
    username = input("Enter admin username [admin]: ").strip() or "admin"
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalars().first():
            print(f"Error: User '{username}' already exists!")
            sys.exit(1)
            
        email = input("Enter admin email: ").strip()
        
        while True:
            password = getpass.getpass("Enter admin password: ")
            confirm = getpass.getpass("Confirm password: ")
            
            if password != confirm:
                print("Error: Passwords do not match. Try again.")
                continue
                
            if len(password) < 8:
                print("Error: Password must be at least 8 characters long.")
                continue
                
            break
            
        # Create an Admin role if it doesn't exist
        role_result = await db.execute(select(Role).where(Role.name == "Admin"))
        admin_role = role_result.scalars().first()
        
        if not admin_role:
            admin_role = Role(name="Admin", description="Super Administrator")
            db.add(admin_role)
            await db.flush()

        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            display_name="System Administrator"
        )
        user.roles.append(admin_role)
        
        db.add(user)
        await db.commit()
        print(f"\n[SUCCESS] Admin user '{username}' created successfully.")

if __name__ == "__main__":
    asyncio.run(main())
