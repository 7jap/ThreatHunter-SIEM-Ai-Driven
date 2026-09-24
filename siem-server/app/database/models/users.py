from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.models.base import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

# Association tables for many-to-many relationships
user_roles = Table(
    'user_roles', Base.metadata,
    Column('user_id', String, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('role_id', String, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True)
)

role_permissions = Table(
    'role_permissions', Base.metadata,
    Column('role_id', String, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True),
    Column('permission_id', String, ForeignKey('permissions.id', ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)
    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    roles = relationship("Role", secondary=user_roles, back_populates="users", lazy="selectin")

class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, index=True, nullable=False) # e.g. Admin, SOC Analyst
    description = Column(String, nullable=True)

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles", lazy="selectin")

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, index=True, nullable=False) # e.g. alerts.view
    description = Column(String, nullable=True)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
