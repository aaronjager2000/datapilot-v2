"""
Webhook API endpoints.

Handles webhook CRUD operations, testing, logs, and inbound webhook processing
with proper authentication, permissions, and signature verification.
"""

import logging
import time
import json
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.tenant import get_current_organization_id
from app.api.v1.dependencies.permissions import require_permission
from app.models import User, Webhook, WebhookLog, Dataset
from app.schemas.webhook import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookListResponse,
    WebhookLogResponse,
    WebhookLogListResponse,
    WebhookWithLogsResponse,
    WebhookTestRequest,
    WebhookTestResponse,
    InboundWebhookResponse,
)
from app.utils.webhook import (
    trigger_webhook,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def validate_webhook_url(url: str) -> bool:
    """
    Validate that a webhook URL is reachable.
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL is reachable, False otherwise
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            # Try OPTIONS request first (least intrusive)
            try:
                response = await client.options(url)
                return True
            except:
                # If OPTIONS fails, try HEAD
                response = await client.head(url)
                return True
    except Exception as e:
        logger.warning(f"Failed to validate webhook URL {url}: {str(e)}")
        return False


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("org:manage"))]
)
async def create_webhook(
    webhook_data: WebhookCreate,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new webhook.
    
    Requires `org:manage` permission.
    
    - Validates webhook URL is reachable
    - Generates secure webhook secret
    - Sets default retry configuration
    
    Args:
        webhook_data: Webhook configuration
        organization_id: Current organization ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Created webhook with secret
    """
    logger.info(
        f"Creating webhook '{webhook_data.name}' for organization {organization_id} "
        f"by user {current_user.id}"
    )
    
    # Validate URL is reachable
    is_valid = await validate_webhook_url(webhook_data.url)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook URL {webhook_data.url} is not reachable"
        )
    
    # Generate secret
    secret = Webhook.generate_secret()
    
    # Get retry config or use defaults
    retry_config = webhook_data.retry_config or Webhook.get_default_retry_config()
    
    # Create webhook
    webhook = Webhook(
        organization_id=organization_id,
        name=webhook_data.name,
        url=webhook_data.url,
        secret=secret,
        events=webhook_data.events,
        is_active=webhook_data.is_active,
        retry_config=retry_config
    )
    
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    
    logger.info(f"Created webhook {webhook.id} for organization {organization_id}")
    
    return webhook


@router.get(
    "",
    response_model=WebhookListResponse
)
async def list_webhooks(
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None
):
    """
    List webhooks for the current organization.
    
    Args:
        organization_id: Current organization ID
        current_user: Current authenticated user
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
    
    Returns:
        List of webhooks
    """
    # Build query
    query = select(Webhook).where(Webhook.organization_id == organization_id)
    
    if is_active is not None:
        query = query.where(Webhook.is_active == is_active)
    
    query = query.order_by(desc(Webhook.created_at))
    
    # Get total count
    count_query = select(func.count()).select_from(Webhook).where(
        Webhook.organization_id == organization_id
    )
    if is_active is not None:
        count_query = count_query.where(Webhook.is_active == is_active)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get webhooks
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    webhooks = result.scalars().all()
    
    return WebhookListResponse(webhooks=webhooks, total=total)


@router.get(
    "/{webhook_id}",
    response_model=WebhookWithLogsResponse
)
async def get_webhook(
    webhook_id: UUID,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_logs: bool = Query(True, description="Include recent logs")
):
    """
    Get webhook details with optional delivery logs.
    
    Args:
        webhook_id: Webhook ID
        organization_id: Current organization ID
        current_user: Current authenticated user
        db: Database session
        include_logs: Whether to include recent logs
    
    Returns:
        Webhook details with logs
    """
    # Get webhook
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.organization_id == organization_id
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    # Convert to response model
    webhook_dict = {
        "id": webhook.id,
        "organization_id": webhook.organization_id,
        "name": webhook.name,
        "url": webhook.url,
        "secret": webhook.secret,
        "events": webhook.events,
        "is_active": webhook.is_active,
        "retry_config": webhook.retry_config,
        "last_triggered": webhook.last_triggered,
        "failure_count": webhook.failure_count,
        "created_at": webhook.created_at,
        "updated_at": webhook.updated_at,
        "recent_logs": []
    }
    
    # Get recent logs if requested
    if include_logs:
        logs_result = await db.execute(
            select(WebhookLog)
            .where(WebhookLog.webhook_id == webhook_id)
            .order_by(desc(WebhookLog.created_at))
            .limit(10)
        )
        logs = logs_result.scalars().all()
        
        webhook_dict["recent_logs"] = [
            WebhookLogResponse(
                id=log.id,
                webhook_id=log.webhook_id,
                event_type=log.event_type,
                payload=log.payload,
                response_status=log.response_status,
                response_body=log.response_body,
                attempt=log.attempt,
                error_message=log.error_message,
                duration_ms=log.duration_ms,
                created_at=log.created_at,
                was_successful=log.was_successful,
                status_category=log.status_category
            )
            for log in logs
        ]
    
    return webhook_dict


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse
)
async def update_webhook(
    webhook_id: UUID,
    webhook_data: WebhookUpdate,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update webhook configuration.
    
    Args:
        webhook_id: Webhook ID
        webhook_data: Updated webhook data
        organization_id: Current organization ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated webhook
    """
    # Get webhook
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.organization_id == organization_id
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    # Validate new URL if provided
    if webhook_data.url is not None:
        is_valid = await validate_webhook_url(webhook_data.url)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook URL {webhook_data.url} is not reachable"
            )
    
    # Update fields
    update_data = webhook_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    
    await db.commit()
    await db.refresh(webhook)
    
    logger.info(f"Updated webhook {webhook_id} in organization {organization_id}")
    
    return webhook


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_webhook(
    webhook_id: UUID,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a webhook.
    
    Args:
        webhook_id: Webhook ID
        organization_id: Current organization ID
        current_user: Current authenticated user
        db: Database session
    """
    # Get webhook
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.organization_id == organization_id
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    await db.delete(webhook)
    await db.commit()
    
    logger.info(f"Deleted webhook {webhook_id} from organization {organization_id}")


@router.post(
    "/{webhook_id}/test",
    response_model=WebhookTestResponse
)
async def test_webhook(
    webhook_id: UUID,
    test_data: WebhookTestRequest,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Send a test webhook with sample payload.
    
    Args:
        webhook_id: Webhook ID to test
        test_data: Test configuration
        organization_id: Current organization ID
        current_user: Current authenticated user
        db: Database session
        background_tasks: Background task manager
    
    Returns:
        Test result with status and response
    """
    # Get webhook
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.organization_id == organization_id
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    logger.info(f"Testing webhook {webhook_id}")
    
    # Trigger webhook with test payload
    success = await trigger_webhook(
        webhook_id=str(webhook_id),
        event_type=test_data.event_type,
        payload=test_data.payload,
        db=db
    )
    
    # Get the most recent log entry
    log_result = await db.execute(
        select(WebhookLog)
        .where(WebhookLog.webhook_id == webhook_id)
        .order_by(desc(WebhookLog.created_at))
        .limit(1)
    )
    log = log_result.scalar_one_or_none()
    
    if log:
        return WebhookTestResponse(
            success=success,
            status_code=log.response_status,
            response_body=log.response_body,
            error_message=log.error_message,
            duration_ms=log.duration_ms
        )
    else:
        return WebhookTestResponse(
            success=False,
            error_message="No log entry created"
        )


@router.get(
    "/{webhook_id}/logs",
    response_model=WebhookLogListResponse
)
async def get_webhook_logs(
    webhook_id: UUID,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, description="Filter by status: success, error, pending")
):
    """
    Get webhook delivery logs.
    
    Args:
        webhook_id: Webhook ID
        organization_id: Current organization ID
        current_user: Current authenticated user
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        event_type: Filter by event type
        status_filter: Filter by status (success, error, pending)
    
    Returns:
        List of webhook logs with delivery details
    """
    # Verify webhook belongs to organization
    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.organization_id == organization_id
        )
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    # Build query
    query = select(WebhookLog).where(WebhookLog.webhook_id == webhook_id)
    
    if event_type:
        query = query.where(WebhookLog.event_type == event_type)
    
    if status_filter:
        if status_filter == "success":
            query = query.where(
                WebhookLog.response_status.between(200, 299)
            )
        elif status_filter == "error":
            query = query.where(
                (WebhookLog.response_status < 200) | (WebhookLog.response_status >= 300)
            )
    
    query = query.order_by(desc(WebhookLog.created_at))
    
    # Get total count
    count_query = select(func.count()).select_from(WebhookLog).where(
        WebhookLog.webhook_id == webhook_id
    )
    if event_type:
        count_query = count_query.where(WebhookLog.event_type == event_type)
    if status_filter:
        if status_filter == "success":
            count_query = count_query.where(
                WebhookLog.response_status.between(200, 299)
            )
        elif status_filter == "error":
            count_query = count_query.where(
                (WebhookLog.response_status < 200) | (WebhookLog.response_status >= 300)
            )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get logs
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Convert to response models
    log_responses = [
        WebhookLogResponse(
            id=log.id,
            webhook_id=log.webhook_id,
            event_type=log.event_type,
            payload=log.payload,
            response_status=log.response_status,
            response_body=log.response_body,
            attempt=log.attempt,
            error_message=log.error_message,
            duration_ms=log.duration_ms,
            created_at=log.created_at,
            was_successful=log.was_successful,
            status_category=log.status_category
        )
        for log in logs
    ]
    
    return WebhookLogListResponse(logs=log_responses, total=total)


@router.post(
    "/inbound/{webhook_id}",
    response_model=InboundWebhookResponse
)
async def receive_inbound_webhook(
    webhook_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive data via inbound webhook from external sources.
    
    This endpoint allows external systems to push data into DataPilot.
    
    - Verifies webhook signature
    - Parses JSON payload
    - Creates dataset from payload
    - Returns success status
    
    Args:
        webhook_id: Webhook ID for authentication
        request: Raw request object
        db: Database session
    
    Returns:
        Success status and dataset ID if created
    """
    # Get webhook
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )
    
    if not webhook.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook is inactive"
        )
    
    # Get signature from header
    signature = request.headers.get("X-Webhook-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature"
        )
    
    # Get raw body
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # Verify signature
    is_valid = verify_webhook_signature(body_str, signature, webhook.secret)
    if not is_valid:
        logger.warning(f"Invalid signature for inbound webhook {webhook_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse JSON payload
    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Extract dataset information from payload
    dataset_name = payload.get("name", f"Inbound webhook data - {webhook.name}")
    dataset_data = payload.get("data", payload)  # Use 'data' field or entire payload
    
    # TODO: Create dataset from payload
    # For now, just log and return success
    logger.info(
        f"Received inbound webhook data for webhook {webhook_id}: "
        f"{len(body_str)} bytes, {len(dataset_data)} records"
    )
    
    # Note: Actual dataset creation would happen here
    # This would involve:
    # 1. Creating a Dataset record
    # 2. Storing the data in storage backend
    # 3. Triggering processing pipeline
    
    return InboundWebhookResponse(
        success=True,
        message=f"Received {len(dataset_data)} records",
        dataset_id=None  # Would be actual dataset ID after creation
    )
