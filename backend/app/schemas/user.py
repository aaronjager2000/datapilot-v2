"""
User Pydantic schemas for request/response validation.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseDBSchema, BaseSchema
from app.schemas.organization import OrganizationSimple


# Base User Schema (shared fields)
class UserBase(BaseSchema):
    """Base user schema with common fields."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


# Create User Request (Registration)
class UserCreate(UserBase):
    """Schema for creating a new user (registration)."""
    password: str = Field(..., min_length=8, max_length=100)
    organization_name: Optional[str] = Field(None, min_length=1, max_length=255)
    organization_slug: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# Update User Request
class UserUpdate(BaseSchema):
    """Schema for updating a user (all fields optional)."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Validate password strength if provided."""
        if v:
            if len(v) < 8:
                raise ValueError("Password must be at least 8 characters long")
            if not any(c.isupper() for c in v):
                raise ValueError("Password must contain at least one uppercase letter")
            if not any(c.islower() for c in v):
                raise ValueError("Password must contain at least one lowercase letter")
            if not any(c.isdigit() for c in v):
                raise ValueError("Password must contain at least one digit")
        return v


# User Response (what API returns)
class UserResponse(UserBase, BaseDBSchema):
    """Schema for user responses."""
    organization_id: UUID
    is_active: bool
    is_superuser: bool
    email_verified: bool
    last_login: Optional[datetime] = None

    # OAuth fields
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None

    # Nested organization (optional)
    organization: Optional[OrganizationSimple] = None


# Simplified User Response (for nested responses)
class UserSimple(BaseSchema):
    """Simplified user schema for nested responses."""
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool


# User with Roles Response
class UserWithRoles(UserResponse):
    """User response with roles included."""
    roles: list[str] = []  # List of role names
    permissions: list[str] = []  # List of permission names


# Invite User to Organization
class UserInvite(BaseSchema):
    """Schema for inviting a user to an organization."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role_ids: list[UUID] = Field(default_factory=list)


# Update User Status (Admin only)
class UserStatusUpdate(BaseSchema):
    """Schema for updating user status."""
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    email_verified: Optional[bool] = None


# Change Password Request
class PasswordChange(BaseSchema):
    """Schema for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# Reset Password Request (Forgot Password)
class PasswordResetRequest(BaseSchema):
    """Schema for requesting password reset."""
    email: EmailStr


# Reset Password Confirmation
class PasswordResetConfirm(BaseSchema):
    """Schema for confirming password reset with token."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# Email Verification
class EmailVerificationRequest(BaseSchema):
    """Schema for email verification."""
    token: str
