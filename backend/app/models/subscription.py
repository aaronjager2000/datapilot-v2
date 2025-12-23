"""
Subscription Model

Tracks organization subscriptions and Stripe billing
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class Subscription(Base):
    """Subscription model for tracking organization billing"""

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Stripe IDs
    stripe_customer_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String, unique=True, nullable=True, index=True
    )
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Plan details
    plan_id: Mapped[str] = mapped_column(String, default="free")
    tier: Mapped[str] = mapped_column(
        String, default="free"
    )  # free, pro, enterprise
    status: Mapped[str] = mapped_column(
        String, default="active"
    )  # active, trialing, canceled, past_due, incomplete

    # Billing period
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)

    # Trial
    trial_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Usage tracking (for current period)
    usage_users: Mapped[int] = mapped_column(Integer, default=0)
    usage_datasets: Mapped[int] = mapped_column(Integer, default=0)
    usage_storage_gb: Mapped[float] = mapped_column(Float, default=0.0)
    usage_api_calls: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="subscription"
    )

    def __repr__(self) -> str:
        return f"<Subscription {self.id} - {self.tier}>"


class SubscriptionPlan(Base):
    """Subscription plan definitions"""

    __tablename__ = "subscription_plans"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Plan details
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    tier: Mapped[str] = mapped_column(
        String, unique=True, index=True
    )  # free, pro, enterprise
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Stripe IDs
    stripe_monthly_price_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    stripe_yearly_price_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )

    # Pricing (in cents)
    price_monthly: Mapped[int] = mapped_column(Integer, default=0)
    price_yearly: Mapped[int] = mapped_column(Integer, default=0)

    # Limits
    max_users: Mapped[int] = mapped_column(Integer, default=1)
    max_datasets: Mapped[int] = mapped_column(Integer, default=5)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=1)
    max_api_calls_per_month: Mapped[int] = mapped_column(Integer, default=1000)

    # Features (JSON array)
    features: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<SubscriptionPlan {self.name}>"
