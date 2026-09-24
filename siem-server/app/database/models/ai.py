from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database.models.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class AIProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, index=True, nullable=False) # LocalOllama, OpenAI, Anthropic
    endpoint = Column(String, nullable=True)
    model = Column(String, nullable=True)
    api_key_encrypted = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    timeout = Column(Integer, default=60)
    max_tokens = Column(Integer, default=4096)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class AIJob(Base):
    __tablename__ = "ai_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    alert_id = Column(String, ForeignKey("alerts.id", ondelete="CASCADE"), index=True, nullable=False)
    priority = Column(String, default="MEDIUM") # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String, default="PENDING") # PENDING, PROCESSING, COMPLETED, FAILED
    attempts = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at")

class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String, nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    context_references = Column(JSON, nullable=True) # References to alerts or data used
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("AIConversation", back_populates="messages")
