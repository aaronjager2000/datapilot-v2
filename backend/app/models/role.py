"""
Role model - represents user roles within organizations.

Roles define sets of permissions that can be assigned to users.
Each organization has its own set of roles (Admin, Manager, Analyst, Viewer).
"""

from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.permission import Permission


class Role(BaseModel):
    """
    Role model - defines user roles within an organization.

    Roles group permissions together and can be assigned to users.
    Common roles: Admin, Manager, Analyst, Viewer
    """

    __tablename__ = "roles"

    # Role Information
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Role name (e.g., Admin, Manager, Analyst, Viewer)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Description of the role and its permissions"
    )

    # Default Role Flag
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this role is assigned to new users by default"
    )

    # System Role Flag (cannot be deleted)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a system-defined role (cannot be deleted)"
    )

    # Relationships
    # users: Mapped[list["User"]] = relationship(
    #     secondary="user_roles",
    #     back_populates="roles"
    # )
    # permissions: Mapped[list["Permission"]] = relationship(
    #     secondary="role_permissions",
    #     back_populates="roles"
    # )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', org_id={self.organization_id})>"


# Association table for many-to-many relationship between users and roles
# This will be created in a separate file or can be defined here
# user_roles = Table(
#     'user_roles',
#     Base.metadata,
#     Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
#     Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
#     Column('created_at', DateTime(timezone=True), server_default=func.now())
# )
