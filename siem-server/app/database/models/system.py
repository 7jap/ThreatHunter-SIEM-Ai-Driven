from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON
from datetime import datetime, timezone
import uuid
from app.database.models.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, index=True, nullable=True) # ID of user taking action, nullable for system actions
    action = Column(String, index=True, nullable=False) # e.g. AGENT_APPROVED
    target_type = Column(String, nullable=True) # e.g. AGENT, USER, ALERT
    target_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(JSON, nullable=False)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Backup(Base):
    __tablename__ = "backups"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String, nullable=False)
    status = Column(String, default="PENDING") # PENDING, SUCCESS, FAILED
    
    created_by = Column(String, nullable=True) # User ID who initiated
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
