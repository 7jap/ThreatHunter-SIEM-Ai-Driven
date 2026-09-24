from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text
from datetime import datetime, timezone
from database.session import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    hostname = Column(String, nullable=True)
    status = Column(String, default="PENDING")
    suricata_version = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, index=True, nullable=False) # Agent side UUID
    agent_id = Column(String, index=True, nullable=False)
    timestamp = Column(String, nullable=False) # From Suricata
    payload = Column(JSON, nullable=False)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
