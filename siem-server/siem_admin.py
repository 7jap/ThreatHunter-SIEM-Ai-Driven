import argparse
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

# Setup DB path relative to server
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.database.models import Agent
from app.database.session import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def list_agents():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        print(f"{'ID':<15} | {'Hostname':<20} | {'Status':<15} | {'Last Seen'}")
        print("-" * 75)
        for a in agents:
            last_seen = a.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") if a.last_heartbeat else "Never"
            print(f"{a.id:<15} | {a.hostname:<20} | {a.status:<15} | {last_seen}")

async def approve_agent(agent_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalars().first()
        if not agent:
            print(f"Error: Agent {agent_id} not found.")
            return
            
        if agent.status == "ACTIVE":
            print(f"Agent {agent_id} is already ACTIVE.")
            return
            
        agent.status = "ACTIVE"
        await session.commit()
        print(f"Success: Agent {agent_id} ({agent.hostname}) is now ACTIVE.")

async def main():
    parser = argparse.ArgumentParser(description="SIEM Server Administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all registered agents")
    
    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Approve a PENDING agent")
    approve_parser.add_argument("agent_id", type=str, help="The ID of the agent to approve")
    
    args = parser.parse_args()
    
    if args.command == "list":
        await list_agents()
    elif args.command == "approve":
        await approve_agent(args.agent_id)

if __name__ == "__main__":
    asyncio.run(main())
