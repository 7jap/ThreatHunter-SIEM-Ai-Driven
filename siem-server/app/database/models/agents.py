from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text, ForeignKey
from datetime import datetime, timezone
from app.database.models.base import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True) # The agent_id
    hostname = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    os_info = Column(String, nullable=True)
    
    status = Column(String, default="PENDING") # PENDING, ACTIVE, DISABLED, REVOKED
    approval_status = Column(String, default="PENDING")
    
    suricata_version = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    
    last_heartbeat = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class AgentToken(Base):
    __tablename__ = "agent_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash = Column(String, nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)
    is_revoked = Column(Boolean, default=False)
