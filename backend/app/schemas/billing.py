"""
Billing Schemas

Pydantic models for billing and subscription
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


# ============================================================================
# Subscription Schemas
# ============================================================================


class SubscriptionBase(BaseModel):
    """Base subscription schema"""

    tier: str
    status: str


class SubscriptionResponse(BaseModel):
    """Subscription response"""

    id: str
    organization_id: str
    stripe_customer_id: str
    stripe_subscription_id: Optional[str] = None
    plan_id: str
    plan_name: str
    tier: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    trial_ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Plan Schemas
# ============================================================================


class PlanLimits(BaseModel):
    """Plan limits"""

    max_users: int
    max_datasets: int
    max_storage_gb: int
    max_api_calls_per_month: int


class PlanResponse(BaseModel):
    """Subscription plan response"""

    id: str
    name: str
    tier: str
    price_monthly: int
    price_yearly: int
    features: List[str]
    limits: PlanLimits

    class Config:
        from_attributes = True


# ============================================================================
# Usage Schemas
# ============================================================================


class UsageMetric(BaseModel):
    """Usage metric"""

    current: int | float
    limit: int


class UsageStatsResponse(BaseModel):
    """Usage statistics response"""

    users: UsageMetric
    datasets: UsageMetric
    storage_gb: UsageMetric
    api_calls: UsageMetric


# ============================================================================
# Checkout Schemas
# ============================================================================


class CheckoutSessionCreate(BaseModel):
    """Create checkout session"""

    plan_id: str
    billing_period: str = Field(default="monthly", pattern="^(monthly|yearly)$")


class CheckoutSessionResponse(BaseModel):
    """Checkout session response"""

    session_id: str
    url: str


class PortalSessionResponse(BaseModel):
    """Portal session response"""

    url: str


# ============================================================================
# Billing History Schemas
# ============================================================================


class BillingHistoryResponse(BaseModel):
    """Billing history item"""

    id: str
    invoice_id: str
    amount: int
    currency: str
    status: str
    invoice_pdf: Optional[str] = None
    description: str
    period_start: int
    period_end: int
    created_at: int


# ============================================================================
# Payment Method Schemas
# ============================================================================


class PaymentMethodResponse(BaseModel):
    """Payment method response"""

    id: str
    type: str
    brand: Optional[str] = None
    last4: str
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool


# ============================================================================
# Common Schemas
# ============================================================================


class MessageResponse(BaseModel):
    """Simple message response"""

    message: str
