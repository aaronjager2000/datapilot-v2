"""
Billing API Endpoints

Stripe integration and subscription management
"""

from typing import List, Dict, Any
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPlan
from app.services.billing import BillingService
from app.core.config import settings
from app.schemas.billing import (
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PortalSessionResponse,
    SubscriptionResponse,
    UsageStatsResponse,
    PlanResponse,
    BillingHistoryResponse,
    PaymentMethodResponse,
    MessageResponse,
)

router = APIRouter()


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get current subscription"""
    result = await db.execute(
        select(Subscription, SubscriptionPlan)
        .join(
            SubscriptionPlan,
            Subscription.plan_id == SubscriptionPlan.id.cast(str),
        )
        .where(Subscription.organization_id == current_user.organization_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription, plan = row

    return {
        "id": str(subscription.id),
        "organization_id": str(subscription.organization_id),
        "stripe_customer_id": subscription.stripe_customer_id,
        "stripe_subscription_id": subscription.stripe_subscription_id,
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "tier": subscription.tier,
        "status": subscription.status,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "trial_ends_at": subscription.trial_end,
        "created_at": subscription.created_at,
        "updated_at": subscription.updated_at,
    }


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get usage statistics"""
    usage = await BillingService.get_usage_stats(db, current_user.organization_id)
    return usage


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get available subscription plans"""
    result = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.is_active == True, SubscriptionPlan.is_public == True
        )
    )
    plans = result.scalars().all()

    return [
        {
            "id": str(plan.id),
            "name": plan.name,
            "tier": plan.tier,
            "price_monthly": plan.price_monthly,
            "price_yearly": plan.price_yearly,
            "features": (
                plan.features.split(",") if plan.features else []
            ),  # Simple split for now
            "limits": {
                "max_users": plan.max_users,
                "max_datasets": plan.max_datasets,
                "max_storage_gb": plan.max_storage_gb,
                "max_api_calls_per_month": plan.max_api_calls_per_month,
            },
        }
        for plan in plans
    ]


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    checkout_data: CheckoutSessionCreate,
) -> Any:
    """Create Stripe checkout session"""
    try:
        session = await BillingService.create_checkout_session(
            db=db,
            organization_id=current_user.organization_id,
            plan_id=checkout_data.plan_id,
            billing_period=checkout_data.billing_period,
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create Stripe customer portal session"""
    try:
        session = await BillingService.create_portal_session(
            db, current_user.organization_id
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create portal session: {str(e)}"
        )


@router.post("/subscription/cancel", response_model=MessageResponse)
async def cancel_subscription(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Cancel subscription"""
    try:
        await BillingService.cancel_subscription(
            db, current_user.organization_id, at_period_end=True
        )
        return {"message": "Subscription cancelled successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/subscription/resume", response_model=MessageResponse)
async def resume_subscription(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Resume cancelled subscription"""
    try:
        await BillingService.resume_subscription(db, current_user.organization_id)
        return {"message": "Subscription resumed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to resume subscription: {str(e)}"
        )


@router.get("/history", response_model=List[BillingHistoryResponse])
async def get_billing_history(
    limit: int = 12,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get billing history"""
    # Get subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        return []

    # Get invoices from Stripe
    try:
        invoices = stripe.Invoice.list(
            customer=subscription.stripe_customer_id, limit=limit
        )

        return [
            {
                "id": invoice.id,
                "invoice_id": invoice.id,
                "amount": invoice.amount_paid,
                "currency": invoice.currency,
                "status": invoice.status,
                "invoice_pdf": invoice.invoice_pdf,
                "description": invoice.lines.data[0].description
                if invoice.lines.data
                else "Subscription",
                "period_start": invoice.period_start,
                "period_end": invoice.period_end,
                "created_at": invoice.created,
            }
            for invoice in invoices.data
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch billing history: {str(e)}"
        )


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get payment methods"""
    # Get subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        return []

    # Get payment methods from Stripe
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=subscription.stripe_customer_id, type="card"
        )

        # Get default payment method
        customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
        default_pm = (
            customer.invoice_settings.default_payment_method
            if customer.invoice_settings
            else None
        )

        return [
            {
                "id": pm.id,
                "type": pm.type,
                "brand": pm.card.brand if pm.card else None,
                "last4": pm.card.last4 if pm.card else None,
                "exp_month": pm.card.exp_month if pm.card else None,
                "exp_year": pm.card.exp_year if pm.card else None,
                "is_default": pm.id == default_pm,
            }
            for pm in payment_methods.data
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch payment methods: {str(e)}"
        )


@router.post("/payment-methods/default", response_model=MessageResponse)
async def set_default_payment_method(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    data: Dict[str, str],
) -> Any:
    """Set default payment method"""
    payment_method_id = data.get("payment_method_id")
    if not payment_method_id:
        raise HTTPException(status_code=400, detail="Payment method ID required")

    # Get subscription
    result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    try:
        # Set as default in Stripe
        stripe.Customer.modify(
            subscription.stripe_customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )
        return {"message": "Default payment method updated"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update payment method: {str(e)}"
        )


@router.delete("/payment-methods/{payment_method_id}", response_model=MessageResponse)
async def remove_payment_method(
    payment_method_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Remove payment method"""
    try:
        stripe.PaymentMethod.detach(payment_method_id)
        return {"message": "Payment method removed"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to remove payment method: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    stripe_signature: str = Header(None),
) -> Any:
    """Handle Stripe webhooks"""
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        await BillingService.handle_checkout_completed(db, event["data"]["object"])
    elif event["type"] == "customer.subscription.updated":
        await BillingService.handle_subscription_updated(db, event["data"]["object"])
    elif event["type"] == "customer.subscription.deleted":
        await BillingService.handle_subscription_deleted(db, event["data"]["object"])
    elif event["type"] == "invoice.paid":
        await BillingService.handle_invoice_paid(db, event["data"]["object"])
    elif event["type"] == "invoice.payment_failed":
        await BillingService.handle_invoice_payment_failed(
            db, event["data"]["object"]
        )

    return {"status": "success"}
