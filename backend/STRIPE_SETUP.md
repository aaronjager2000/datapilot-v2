# Stripe Integration Setup

This document outlines the steps needed to complete the Stripe billing integration.

## Environment Variables

Add the following to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Database Migration

Run the migration to create subscription tables:

```bash
alembic revision --autogenerate -m "Add subscription tables"
alembic upgrade head
```

## Seed Subscription Plans

Create a script to seed the initial subscription plans:

```python
# scripts/seed_plans.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.subscription import SubscriptionPlan
from app.core.config import settings

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

plans = [
    {
        "name": "Free",
        "tier": "free",
        "price_monthly": 0,
        "price_yearly": 0,
        "max_users": 1,
        "max_datasets": 5,
        "max_storage_gb": 1,
        "max_api_calls_per_month": 1000,
        "features": "5 datasets,1 GB storage,1000 API calls/month,Community support",
        "is_active": True,
        "is_public": True,
    },
    {
        "name": "Pro",
        "tier": "pro",
        "stripe_monthly_price_id": "price_...",  # Set from Stripe dashboard
        "stripe_yearly_price_id": "price_...",   # Set from Stripe dashboard
        "price_monthly": 2900,  # $29.00
        "price_yearly": 29000,  # $290.00 (save ~20%)
        "max_users": 10,
        "max_datasets": 100,
        "max_storage_gb": 50,
        "max_api_calls_per_month": 100000,
        "features": "100 datasets,50 GB storage,100K API calls/month,Priority support,Advanced analytics,Custom integrations",
        "is_active": True,
        "is_public": True,
    },
    {
        "name": "Enterprise",
        "tier": "enterprise",
        "stripe_monthly_price_id": "price_...",  # Set from Stripe dashboard
        "stripe_yearly_price_id": "price_...",   # Set from Stripe dashboard
        "price_monthly": 9900,  # $99.00
        "price_yearly": 99000,  # $990.00
        "max_users": 999,
        "max_datasets": 9999,
        "max_storage_gb": 500,
        "max_api_calls_per_month": 1000000,
        "features": "Unlimited datasets,500 GB storage,1M API calls/month,24/7 support,Advanced analytics,Custom integrations,SSO,SLA",
        "is_active": True,
        "is_public": True,
    },
]

with Session(engine) as session:
    for plan_data in plans:
        plan = SubscriptionPlan(**plan_data)
        session.add(plan)
    session.commit()
    print("Plans seeded successfully!")
```

## Stripe Dashboard Setup

1. **Create Products & Prices**:
   - Go to Stripe Dashboard > Products
   - Create products for Pro and Enterprise plans
   - Create both monthly and yearly prices for each
   - Copy the price IDs and add them to the seed script

2. **Configure Webhook**:
   - Go to Stripe Dashboard > Developers > Webhooks
   - Add endpoint: `https://your-domain.com/api/v1/billing/webhook`
   - Select events:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.paid`
     - `invoice.payment_failed`
   - Copy the webhook secret to `.env`

3. **Test Mode**:
   - Use test keys during development
   - Use test card: `4242 4242 4242 4242`

## API Router Registration

Add the billing router to your API:

```python
# app/api/v1/api.py
from app.api.v1.endpoints import billing

api_router.include_router(
    billing.router,
    prefix="/billing",
    tags=["billing"]
)
```

## Organization Model Update

Update the Organization model to include the subscription relationship:

```python
# app/models/organization.py
from sqlalchemy.orm import relationship

class Organization(Base):
    # ... existing fields ...
    
    # Add relationship
    subscription: Mapped["Subscription"] = relationship(
        "Subscription",
        back_populates="organization",
        uselist=False
    )
```

## Automatic Subscription Creation

Update user registration to create a free subscription:

```python
# app/api/v1/endpoints/auth.py or wherever you create organizations
from app.services.billing import BillingService

# After creating organization:
await BillingService.create_customer(
    db=db,
    organization_id=organization.id,
    email=user.email,
    name=organization.name
)
```

## Usage Tracking

Implement usage tracking in relevant endpoints:

```python
# Example: After creating a dataset
from app.services.billing import BillingService

await BillingService.increment_usage(
    db=db,
    organization_id=current_user.organization_id,
    metric="datasets",
    amount=1
)
```

## Monthly Reset Cron Job

Set up a cron job to reset monthly usage:

```python
# scripts/reset_monthly_usage.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.billing import BillingService
from app.core.config import settings

async def reset_usage():
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        await BillingService.reset_monthly_usage(session)
        print("Monthly usage reset completed")

if __name__ == "__main__":
    asyncio.run(reset_usage())
```

Add to crontab:
```bash
0 0 1 * * cd /path/to/backend && python scripts/reset_monthly_usage.py
```

## Testing

1. Test checkout flow in test mode
2. Test webhook delivery using Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/billing/webhook
   ```
3. Test subscription updates, cancellations, and resumptions
4. Test usage tracking and limits

## Security Notes

- Never commit Stripe keys to version control
- Use environment variables for all secrets
- Verify webhook signatures
- Implement rate limiting on webhook endpoint
- Log all billing events for audit trail
- Test thoroughly in Stripe test mode before going live

## Going Live

1. Switch to live Stripe keys
2. Create live products and prices
3. Update webhook endpoint to production URL
4. Test with small transaction
5. Monitor logs for errors
6. Set up alerts for payment failures
