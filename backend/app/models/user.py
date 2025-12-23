"""
User model - represents users within organizations.

Users belong to organizations and have roles that define their permissions.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.permission import user_roles

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.role import Role
    from app.models.dataset import Dataset
    from app.models.file import File
    from app.models.visualization import Visualization
    from app.models.dashboard import Dashboard


class User(BaseModel):
    """
    User model - represents application users.

    Users are scoped to organizations (multi-tenant).
    Each user has roles that define their permissions within their organization.
    """

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User's email address (used for login)"
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )

    # Profile Information
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's full name"
    )

    # Account Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether the user account is active"
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the user has superuser privileges (can access all organizations)"
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the user has verified their email address"
    )

    # Login Tracking
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the user's last login"
    )

    # OAuth Support (optional)
    oauth_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="OAuth provider (e.g., 'google', 'github')"
    )

    oauth_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User's ID from the OAuth provider"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="users"
    )
    
    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
        foreign_keys=[user_roles.c.user_id, user_roles.c.role_id]
    )

    datasets: Mapped[list["Dataset"]] = relationship(
        "Dataset",
        back_populates="creator",
        foreign_keys="Dataset.created_by"
    )

    uploaded_files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="uploader",
        foreign_keys="File.uploaded_by"
    )

    visualizations: Mapped[list["Visualization"]] = relationship(
        "Visualization",
        back_populates="creator",
        foreign_keys="Visualization.created_by"
    )

    dashboards: Mapped[list["Dashboard"]] = relationship(
        "Dashboard",
        back_populates="creator",
        foreign_keys="Dashboard.created_by"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', org_id={self.organization_id})>"

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (active account)."""
        return self.is_active

    @property
    def display_name(self) -> str:
        """Get user's display name."""
        return self.full_name or self.email.split("@")[0]


# Association table for many-to-many relationship between users and roles
# This will be created in a separate file or can be defined here
# user_roles = Table(
#     'user_roles',
#     Base.metadata,
#     Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
#     Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
#     Column('created_at', DateTime(timezone=True), server_default=func.now())
# )
