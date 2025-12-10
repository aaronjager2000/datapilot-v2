"""
Permission model - defines granular permissions in the system.

Permissions are global (not organization-specific) and define what actions
users can perform. Permissions are assigned to roles or directly to users.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Table, Column, ForeignKey, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.user import User


class Permission(Base):
    """
    Permission model - defines system-wide permissions.
    
    Permissions are not organization-specific. They define actions like:
    - data:import, data:export, data:view, data:edit, data:delete
    - org:manage, org:view, org:billing
    - dashboard:create, dashboard:edit, dashboard:delete
    - user:invite, user:manage
    """
    
    __tablename__ = "permissions"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="Permission unique identifier"
    )
    
    # Permission Identification
    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Permission code (e.g., 'data:import', 'org:manage')"
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name for the permission"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Description of what this permission allows"
    )
    
    # Permission Category
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Category: data, org, dashboard, user, billing, etc."
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Permission(code='{self.code}', name='{self.name}', category='{self.category}')>"


# Association table: Role -> Permissions (many-to-many)
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)


# Association table: User -> Roles (many-to-many)
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
)


# Association table: User -> Permissions (for direct permission overrides)
user_permissions = Table(
    'user_permissions',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('granted', Boolean, default=True, comment='True=grant, False=revoke'),
    Column('created_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
)
