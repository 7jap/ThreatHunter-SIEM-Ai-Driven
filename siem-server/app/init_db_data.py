import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from app.database.session import AsyncSessionLocal
from app.database.models.users import Permission, Role
from app.core.permissions import Permissions

from sqlalchemy.orm import selectinload

async def init_data():
    async with AsyncSessionLocal() as db:
        print("[*] Synchronizing System Permissions...")
        
        # 1. Ensure all permissions exist
        all_perms = Permissions.get_all()
        existing_perms_result = await db.execute(select(Permission))
        existing_perms = existing_perms_result.scalars().all()
        existing_names = {p.name for p in existing_perms}
        
        db_perms = list(existing_perms)
        
        added_count = 0
        for p_name in all_perms:
            if p_name not in existing_names:
                new_perm = Permission(name=p_name, description=f"Allows {p_name}")
                db.add(new_perm)
                db_perms.append(new_perm)
                added_count += 1
                
        await db.commit()
        print(f"[*] Added {added_count} new permissions.")
        
        # 2. Ensure Admin role exists with all permissions
        role_res = await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.name == "Admin"))
        admin_role = role_res.scalars().first()
        if not admin_role:
            admin_role = Role(name="Admin", description="Super Administrator with all permissions")
            admin_role.permissions = db_perms
            db.add(admin_role)
            print("[*] Created 'Admin' role.")
        else:
            admin_role.permissions = db_perms
        
        # 3. Create SOC Analyst default role
        soc_res = await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.name == "SOC Analyst"))
        soc_role = soc_res.scalars().first()
        if not soc_role:
            soc_role = Role(name="SOC Analyst", description="Security Operations Center Analyst")
            
            soc_perm_names = [
                Permissions.ALERTS_VIEW, Permissions.ALERTS_SEARCH, Permissions.ALERTS_INVESTIGATE,
                Permissions.AGENTS_VIEW, Permissions.AI_CHAT, Permissions.AI_INVESTIGATE, Permissions.AI_VIEW
            ]
            soc_role.permissions = [p for p in db_perms if p.name in soc_perm_names]
            db.add(soc_role)
            print("[*] Created 'SOC Analyst' role.")
        else:
            soc_perm_names = [
                Permissions.ALERTS_VIEW, Permissions.ALERTS_SEARCH, Permissions.ALERTS_INVESTIGATE,
                Permissions.AGENTS_VIEW, Permissions.AI_CHAT, Permissions.AI_INVESTIGATE, Permissions.AI_VIEW
            ]
            soc_role.permissions = [p for p in db_perms if p.name in soc_perm_names]
            
        await db.commit()
        
        print("[*] RBAC Initialization Complete. All roles and permissions are up to date.")

if __name__ == "__main__":
    asyncio.run(init_data())
