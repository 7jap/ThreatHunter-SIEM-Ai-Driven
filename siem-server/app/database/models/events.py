from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database.models.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, index=True, nullable=False) # Agent side UUID
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp = Column(String, nullable=False) # From Suricata
    event_type = Column(String, nullable=True) # e.g. "alert", "dns"
    source = Column(String, nullable=True) # e.g. "suricata"
    payload = Column(JSON, nullable=False)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), unique=True, nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    severity = Column(Integer, nullable=True)
    signature = Column(String, index=True, nullable=True)
    category = Column(String, nullable=True)
    
    source_ip = Column(String, index=True, nullable=True)
    source_port = Column(Integer, nullable=True)
    destination_ip = Column(String, index=True, nullable=True)
    destination_port = Column(Integer, nullable=True)
    protocol = Column(String, nullable=True)
    direction = Column(String, nullable=True)
    
    status = Column(String, default="NEW", index=True) # NEW, PENDING, ANALYZING, COMPLETED, FAILED
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    ai_analysis = relationship("AlertAIAnalysis", back_populates="alert", uselist=False, cascade="all, delete-orphan")

class AlertRelation(Base):
    __tablename__ = "alert_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    primary_alert_id = Column(String, ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    related_alert_id = Column(String, ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AlertAIAnalysis(Base):
    __tablename__ = "alert_ai_analysis"

    id = Column(String, primary_key=True, default=generate_uuid)
    alert_id = Column(String, ForeignKey("alerts.id", ondelete="CASCADE"), unique=True, index=True)
    provider_id = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    
    analysis_status = Column(String, default="PENDING")
    severity_score = Column(Float, nullable=True) # 0 to 10
    summary = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    techniques = Column(JSON, nullable=True) # Array of strings
    indicators = Column(JSON, nullable=True) # Array of strings
    recommended_investigation = Column(JSON, nullable=True) # Array of strings
    confidence = Column(Float, nullable=True)
    
    raw_response = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    alert = relationship("Alert", back_populates="ai_analysis")
