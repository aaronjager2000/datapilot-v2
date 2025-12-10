from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, Integer, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class SubscriptionTier(str, PyEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    TRIALING = "trialing"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    INCOMPLETE = "incomplete"

class Organization(Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="The name of the organization",
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        unique=True,
        comment="The slug of the organization (URL friendly identifier)",
    )

    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier_enum"),
        default=SubscriptionTier.FREE,
        nullable=False,
        comment="The subscription tier of the organization",
    )

    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status_enum"),
        default=SubscriptionStatus.TRIALING,
        nullable=False,
        comment="Current subscription status",
    )

    max_users: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="Maximum number of users allowed for the organization",
    )

    max_datasets: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        comment="Maximum number of datasets allowed for the organization",
    )

    max_storage_gb: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="Maximum storage allowed for the organization in GB",
    )

    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Stripe customer ID for billing",
    )

    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Stripe subscription ID for billing",
    )
    
    settings: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: {},
        comment="Flexible settings for the organization",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        comment="Whether the organization is active",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}', tier={self.subscription_tier.value})>"
    
    @property
    def is_free_tier(self) -> bool:
        """Check if organization is on free tier."""
        return self.subscription_tier == SubscriptionTier.FREE
    
    @property
    def is_pro_tier(self) -> bool:
        """Check if organization is on pro tier."""
        return self.subscription_tier == SubscriptionTier.PRO
    
    @property
    def is_enterprise_tier(self) -> bool:
        """Check if organization is on enterprise tier."""
        return self.subscription_tier == SubscriptionTier.ENTERPRISE
    
    @property
    def has_active_subscription(self) -> bool:
        """Check if organization has an active subscription."""
        return self.subscription_status in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING
        ]
    
        
    # Relationships
    webhooks: Mapped[list["Webhook"]] = relationship(
        "Webhook",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
