"""
Organization Pydantic schemas for request/response validation.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import BaseDBSchema, BaseSchema


class SubscriptionTierEnum:
    """Subscription tier constants."""
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatusEnum:
    """Subscription status constants."""
    ACTIVE = "ACTIVE"
    TRIALING = "TRIALING"
    CANCELLED = "CANCELLED"
    PAST_DUE = "PAST_DUE"


# Base Organization Schema (shared fields)
class OrganizationBase(BaseSchema):
    """Base organization schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is lowercase and uses hyphens."""
        if not v.islower() or " " in v:
            raise ValueError("Slug must be lowercase with no spaces")
        return v


# Create Organization Request
class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization."""
    pass


# Update Organization Request
class OrganizationUpdate(BaseSchema):
    """Schema for updating an organization (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        """Ensure slug is lowercase and uses hyphens."""
        if v and (not v.islower() or " " in v):
            raise ValueError("Slug must be lowercase with no spaces")
        return v


# Organization Response (what API returns)
class OrganizationResponse(OrganizationBase, BaseDBSchema):
    """Schema for organization responses."""
    subscription_tier: str
    subscription_status: str
    trial_ends_at: Optional[datetime] = None
    is_active: bool

    # Usage Limits
    max_users: int
    max_datasets: int
    max_storage_gb: int

    # Current Usage (computed fields - would come from service layer)
    current_users: Optional[int] = None
    current_datasets: Optional[int] = None
    current_storage_gb: Optional[float] = None

    # Stripe Info (only for admins)
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


# Simplified Organization Response (for nested responses)
class OrganizationSimple(BaseSchema):
    """Simplified organization schema for nested responses."""
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None


# Organization Settings Update
class OrganizationSettingsUpdate(BaseSchema):
    """Schema for updating organization settings."""
    settings: dict = Field(..., description="Organization settings as JSON object")


# Organization Subscription Update (Admin only)
class OrganizationSubscriptionUpdate(BaseSchema):
    """Schema for updating organization subscription."""
    subscription_tier: str = Field(..., pattern=r"^(FREE|PRO|ENTERPRISE)$")
    max_users: Optional[int] = Field(None, ge=1)
    max_datasets: Optional[int] = Field(None, ge=1)
    max_storage_gb: Optional[int] = Field(None, ge=1)


# Organization Statistics Response
class OrganizationStats(BaseSchema):
    """Schema for organization statistics."""
    total_users: int
    active_users: int
    total_datasets: int
    total_storage_gb: float
    total_queries: int
    queries_this_month: int
