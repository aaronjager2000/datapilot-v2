"""
Billing Service

Stripe integration for subscription management
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

import stripe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.subscription import Subscription, SubscriptionPlan
from app.models.organization import Organization
from app.core.config import settings


# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class BillingService:
    """Service for managing Stripe billing and subscriptions"""

    @staticmethod
    async def create_customer(
        db: AsyncSession, organization_id: UUID, email: str, name: str
    ) -> str:
        """Create Stripe customer for organization"""
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"organization_id": str(organization_id)},
        )

        # Create subscription record
        subscription = Subscription(
            organization_id=organization_id,
            stripe_customer_id=customer.id,
            plan_id="free",
            tier="free",
            status="active",
        )
        db.add(subscription)
        await db.commit()

        return customer.id

    @staticmethod
    async def create_checkout_session(
        db: AsyncSession,
        organization_id: UUID,
        plan_id: str,
        billing_period: str = "monthly",
        success_url: str = None,
        cancel_url: str = None,
    ) -> Dict[str, str]:
        """Create Stripe checkout session for plan upgrade"""

        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError("Subscription not found")

        # Get plan
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise ValueError("Plan not found")

        # Get price ID
        price_id = (
            plan.stripe_monthly_price_id
            if billing_period == "monthly"
            else plan.stripe_yearly_price_id
        )
        if not price_id:
            raise ValueError("Price not configured for plan")

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url
            or f"{settings.FRONTEND_URL}/billing?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url or f"{settings.FRONTEND_URL}/billing",
            metadata={
                "organization_id": str(organization_id),
                "plan_id": str(plan_id),
            },
        )

        return {"session_id": session.id, "url": session.url}

    @staticmethod
    async def create_portal_session(
        db: AsyncSession, organization_id: UUID, return_url: str = None
    ) -> Dict[str, str]:
        """Create Stripe customer portal session"""

        # Get subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise ValueError("Subscription not found")

        # Create portal session
        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url or f"{settings.FRONTEND_URL}/billing",
        )

        return {"url": session.url}

    @staticmethod
    async def handle_checkout_completed(
        db: AsyncSession, session: Dict[str, Any]
    ) -> None:
        """Handle successful checkout completion"""
        organization_id = UUID(session["metadata"]["organization_id"])
        subscription_id = session["subscription"]

        # Get Stripe subscription
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)

        # Update subscription record
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one()

        subscription.stripe_subscription_id = subscription_id
        subscription.stripe_price_id = stripe_subscription["items"]["data"][0][
            "price"
        ]["id"]
        subscription.status = stripe_subscription["status"]
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_subscription["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_subscription["current_period_end"]
        )

        # Get plan from metadata
        plan_id = session["metadata"]["plan_id"]
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        plan = result.scalar_one()

        subscription.plan_id = str(plan.id)
        subscription.tier = plan.tier

        # Update organization limits
        result = await db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalar_one()
        org.max_users = plan.max_users
        org.max_datasets = plan.max_datasets
        org.max_storage_gb = plan.max_storage_gb

        await db.commit()

    @staticmethod
    async def handle_subscription_updated(
        db: AsyncSession, stripe_subscription: Dict[str, Any]
    ) -> None:
        """Handle subscription update webhook"""
        subscription_id = stripe_subscription["id"]

        # Find subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        # Update status and period
        subscription.status = stripe_subscription["status"]
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_subscription["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_subscription["current_period_end"]
        )
        subscription.cancel_at_period_end = stripe_subscription[
            "cancel_at_period_end"
        ]

        await db.commit()

    @staticmethod
    async def handle_subscription_deleted(
        db: AsyncSession, stripe_subscription: Dict[str, Any]
    ) -> None:
        """Handle subscription cancellation"""
        subscription_id = stripe_subscription["id"]

        # Find subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        # Downgrade to free plan
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.tier == "free")
        )
        free_plan = result.scalar_one()

        subscription.plan_id = str(free_plan.id)
        subscription.tier = "free"
        subscription.status = "canceled"
        subscription.stripe_subscription_id = None

        # Update organization limits
        result = await db.execute(
            select(Organization).where(
                Organization.id == subscription.organization_id
            )
        )
        org = result.scalar_one()
        org.max_users = free_plan.max_users
        org.max_datasets = free_plan.max_datasets
        org.max_storage_gb = free_plan.max_storage_gb

        await db.commit()

    @staticmethod
    async def handle_invoice_paid(
        db: AsyncSession, invoice: Dict[str, Any]
    ) -> None:
        """Handle successful invoice payment"""
        # You can add logic here to:
        # - Send payment confirmation emails
        # - Update billing history
        # - Track payment metrics
        pass

    @staticmethod
    async def handle_invoice_payment_failed(
        db: AsyncSession, invoice: Dict[str, Any]
    ) -> None:
        """Handle failed invoice payment"""
        customer_id = invoice["customer"]

        # Find subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == customer_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        # Update status
        subscription.status = "past_due"
        await db.commit()

        # You can add logic here to:
        # - Send payment failure notification
        # - Implement retry logic
        # - Suspend account after multiple failures

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession, organization_id: UUID, at_period_end: bool = True
    ) -> None:
        """Cancel subscription"""
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription found")

        # Cancel in Stripe
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=at_period_end,
        )

        # Update local record
        subscription.cancel_at_period_end = at_period_end
        if not at_period_end:
            subscription.status = "canceled"

        await db.commit()

    @staticmethod
    async def resume_subscription(db: AsyncSession, organization_id: UUID) -> None:
        """Resume a cancelled subscription"""
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No subscription found")

        # Resume in Stripe
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False,
        )

        # Update local record
        subscription.cancel_at_period_end = False
        subscription.status = "active"

        await db.commit()

    @staticmethod
    async def get_usage_stats(
        db: AsyncSession, organization_id: UUID
    ) -> Dict[str, Any]:
        """Get usage statistics for organization"""
        # Get subscription with plan limits
        result = await db.execute(
            select(Subscription, SubscriptionPlan)
            .join(
                SubscriptionPlan,
                Subscription.plan_id == SubscriptionPlan.id.cast(str),
            )
            .where(Subscription.organization_id == organization_id)
        )
        row = result.one_or_none()
        if not row:
            raise ValueError("Subscription not found")

        subscription, plan = row

        return {
            "users": {
                "current": subscription.usage_users,
                "limit": plan.max_users,
            },
            "datasets": {
                "current": subscription.usage_datasets,
                "limit": plan.max_datasets,
            },
            "storage_gb": {
                "current": subscription.usage_storage_gb,
                "limit": plan.max_storage_gb,
            },
            "api_calls": {
                "current": subscription.usage_api_calls,
                "limit": plan.max_api_calls_per_month,
            },
        }

    @staticmethod
    async def increment_usage(
        db: AsyncSession,
        organization_id: UUID,
        metric: str,
        amount: float = 1.0,
    ) -> None:
        """Increment usage for a metric"""
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id == organization_id
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return

        if metric == "users":
            subscription.usage_users = int(subscription.usage_users + amount)
        elif metric == "datasets":
            subscription.usage_datasets = int(subscription.usage_datasets + amount)
        elif metric == "storage_gb":
            subscription.usage_storage_gb = subscription.usage_storage_gb + amount
        elif metric == "api_calls":
            subscription.usage_api_calls = int(subscription.usage_api_calls + amount)

        await db.commit()

    @staticmethod
    async def reset_monthly_usage(db: AsyncSession) -> None:
        """Reset monthly usage counters (run via cron)"""
        result = await db.execute(select(Subscription))
        subscriptions = result.scalars().all()

        for subscription in subscriptions:
            subscription.usage_api_calls = 0

        await db.commit()
