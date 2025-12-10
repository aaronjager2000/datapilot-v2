"""
Webhook service - webhook delivery, signature verification, and retry logic.

This module handles webhook event delivery to external systems with proper
HMAC-SHA256 signing, retry logic, and failure tracking.
"""

import hmac
import hashlib
import time
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.webhook import Webhook, WebhookLog
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


def generate_signature(payload: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.
    
    Args:
        payload: JSON string payload to sign
        secret: Secret key for HMAC
    
    Returns:
        Hex-encoded HMAC signature
    """
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.
    
    Args:
        payload: JSON string payload received
        signature: Signature from webhook header
        secret: Secret key for HMAC
    
    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = generate_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)


def calculate_retry_delay(
    attempt: int,
    strategy: str = "exponential",
    initial_delay: int = 60,
    max_delay: int = 3600
) -> int:
    """
    Calculate retry delay based on backoff strategy.
    
    Args:
        attempt: Current attempt number (1-based)
        strategy: Backoff strategy (exponential, linear, constant)
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Delay in seconds
    """
    if strategy == "exponential":
        # Exponential: initial_delay * 2^(attempt-1)
        delay = initial_delay * (2 ** (attempt - 1))
    elif strategy == "linear":
        # Linear: initial_delay * attempt
        delay = initial_delay * attempt
    else:
        # Constant: always use initial_delay
        delay = initial_delay
    
    # Cap at max_delay
    return min(delay, max_delay)


async def trigger_webhook(
    webhook_id: str,
    event_type: str,
    payload: Dict[str, Any],
    db: Optional[AsyncSession] = None,
    attempt: int = 1
) -> bool:
    """
    Trigger a webhook by sending HTTP POST with signed payload.
    
    Args:
        webhook_id: UUID of webhook to trigger
        event_type: Event type (e.g., "dataset.processed")
        payload: Event payload dictionary
        db: Database session (optional, will create if not provided)
        attempt: Current attempt number (1 for first attempt)
    
    Returns:
        True if delivery was successful (2xx response), False otherwise
    """
    # Create DB session if not provided
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True
    
    try:
        # Load webhook from database
        result = await db.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            logger.error(f"Webhook {webhook_id} not found")
            return False
        
        if not webhook.is_active:
            logger.info(f"Webhook {webhook_id} is inactive, skipping delivery")
            return False
        
        # Check if webhook listens for this event type
        if not webhook.has_event(event_type):
            logger.info(f"Webhook {webhook_id} not configured for event {event_type}")
            return False
        
        # Prepare payload
        import json
        full_payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_id": str(webhook_id),
            "attempt": attempt,
            "data": payload
        }
        payload_json = json.dumps(full_payload, default=str)
        
        # Generate signature
        signature = generate_signature(payload_json, webhook.secret)
        
        # Get retry config
        timeout = webhook.get_retry_config("timeout", 30)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type,
            "X-Webhook-ID": str(webhook_id),
            "X-Webhook-Attempt": str(attempt),
            "User-Agent": "DataPilot-Webhook/1.0"
        }
        
        # Make HTTP request
        start_time = time.time()
        response_status = None
        response_body = None
        error_message = None
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers
                )
                response_status = response.status_code
                response_body = response.text[:10000]  # Truncate to 10KB
                
        except httpx.TimeoutException as e:
            error_message = f"Request timeout after {timeout}s"
            logger.warning(f"Webhook {webhook_id} timeout: {error_message}")
            
        except httpx.RequestError as e:
            error_message = f"Request error: {str(e)}"
            logger.warning(f"Webhook {webhook_id} request error: {error_message}")
            
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Webhook {webhook_id} unexpected error: {error_message}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Create log entry
        log = WebhookLog.create_from_delivery(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=full_payload,
            response_status=response_status,
            response_body=response_body,
            attempt=attempt,
            error_message=error_message,
            duration_ms=duration_ms
        )
        db.add(log)
        
        # Update webhook metadata
        webhook.update_last_triggered()
        
        # Check if delivery was successful
        success = log.was_successful
        
        if success:
            webhook.reset_failure_count()
            logger.info(
                f"Webhook {webhook_id} delivered successfully "
                f"(status={response_status}, duration={duration_ms}ms, attempt={attempt})"
            )
        else:
            webhook.increment_failure_count()
            
            # Auto-disable if too many failures
            if webhook.should_auto_disable:
                webhook.is_active = False
                logger.error(
                    f"Webhook {webhook_id} auto-disabled after {webhook.failure_count} failures"
                )
            
            logger.warning(
                f"Webhook {webhook_id} delivery failed "
                f"(status={response_status}, error={error_message}, "
                f"attempt={attempt}, failures={webhook.failure_count})"
            )
            
            # Schedule retry if appropriate
            max_attempts = webhook.get_retry_config("max_attempts", 3)
            if attempt < max_attempts and log.should_retry:
                # Calculate retry delay
                strategy = webhook.get_retry_config("backoff_strategy", "exponential")
                initial_delay = webhook.get_retry_config("initial_delay", 60)
                max_delay = webhook.get_retry_config("max_delay", 3600)
                
                retry_delay = calculate_retry_delay(
                    attempt + 1,
                    strategy,
                    initial_delay,
                    max_delay
                )
                
                logger.info(
                    f"Webhook {webhook_id} will retry in {retry_delay}s "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                
                # Schedule retry as background task
                asyncio.create_task(
                    _retry_webhook_after_delay(
                        webhook_id=str(webhook_id),
                        event_type=event_type,
                        payload=payload,
                        attempt=attempt + 1,
                        delay=retry_delay
                    )
                )
        
        await db.commit()
        return success
        
    except Exception as e:
        logger.error(f"Error triggering webhook {webhook_id}: {str(e)}")
        await db.rollback()
        return False
        
    finally:
        if close_db:
            await db.close()


async def _retry_webhook_after_delay(
    webhook_id: str,
    event_type: str,
    payload: Dict[str, Any],
    attempt: int,
    delay: int
):
    """
    Internal function to retry webhook after delay.
    
    Args:
        webhook_id: Webhook UUID
        event_type: Event type
        payload: Event payload
        attempt: Retry attempt number
        delay: Delay in seconds before retry
    """
    await asyncio.sleep(delay)
    
    logger.info(f"Retrying webhook {webhook_id} (attempt {attempt})")
    
    # Create new DB session for retry
    db = AsyncSessionLocal()
    try:
        await trigger_webhook(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            db=db,
            attempt=attempt
        )
    finally:
        await db.close()


async def retry_failed_webhooks():
    """
    Background task to retry failed webhook deliveries.
    
    This function should be called periodically (e.g., every 5 minutes)
    to retry webhooks that failed but haven't exceeded max attempts.
    
    Looks for webhook logs from the last 24 hours that:
    - Failed delivery (non-2xx status or network error)
    - Should be retried (5xx or network error, not 4xx)
    - Haven't exceeded max_attempts
    - Are for active webhooks
    """
    db = AsyncSessionLocal()
    try:
        # Find failed webhook logs from last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        result = await db.execute(
            select(WebhookLog)
            .join(Webhook)
            .where(
                WebhookLog.created_at >= cutoff_time,
                Webhook.is_active == True,
                # Failed delivery
                (
                    (WebhookLog.response_status == None) |  # Network error
                    (WebhookLog.response_status >= 500)     # Server error
                )
            )
            .order_by(WebhookLog.created_at.asc())
        )
        failed_logs = result.scalars().all()
        
        if not failed_logs:
            logger.info("No failed webhooks to retry")
            return
        
        logger.info(f"Found {len(failed_logs)} failed webhook deliveries to retry")
        
        # Group by webhook_id and event to avoid duplicate retries
        retry_tasks = {}
        for log in failed_logs:
            webhook = log.webhook
            
            # Check if we've exceeded max attempts
            max_attempts = webhook.get_retry_config("max_attempts", 3)
            if log.attempt >= max_attempts:
                continue
            
            # Use latest log for each webhook+event combination
            key = (str(log.webhook_id), log.event_type)
            if key not in retry_tasks or log.created_at > retry_tasks[key].created_at:
                retry_tasks[key] = log
        
        logger.info(f"Retrying {len(retry_tasks)} unique webhook deliveries")
        
        # Trigger retries
        for log in retry_tasks.values():
            try:
                await trigger_webhook(
                    webhook_id=str(log.webhook_id),
                    event_type=log.event_type,
                    payload=log.payload.get("data", {}),
                    db=db,
                    attempt=log.attempt + 1
                )
            except Exception as e:
                logger.error(
                    f"Error retrying webhook {log.webhook_id} for event {log.event_type}: {str(e)}"
                )
        
        logger.info("Finished retrying failed webhooks")
        
    except Exception as e:
        logger.error(f"Error in retry_failed_webhooks: {str(e)}")
        
    finally:
        await db.close()


async def trigger_webhooks_for_event(
    event_type: str,
    payload: Dict[str, Any],
    organization_id: str,
    db: Optional[AsyncSession] = None
):
    """
    Trigger all webhooks for an organization that are configured for an event type.
    
    This is a convenience function to trigger all relevant webhooks for an event.
    
    Args:
        event_type: Event type (e.g., "dataset.processed")
        payload: Event payload
        organization_id: Organization UUID
        db: Database session (optional)
    """
    close_db = False
    if db is None:
        db = AsyncSessionLocal()
        close_db = True
    
    try:
        # Find all active webhooks for this organization and event
        result = await db.execute(
            select(Webhook)
            .where(
                Webhook.organization_id == organization_id,
                Webhook.is_active == True
            )
        )
        webhooks = result.scalars().all()
        
        # Filter webhooks that listen for this event
        matching_webhooks = [w for w in webhooks if w.has_event(event_type)]
        
        if not matching_webhooks:
            logger.info(
                f"No active webhooks found for event {event_type} "
                f"in organization {organization_id}"
            )
            return
        
        logger.info(
            f"Triggering {len(matching_webhooks)} webhooks for event {event_type} "
            f"in organization {organization_id}"
        )
        
        # Trigger all webhooks concurrently
        tasks = [
            trigger_webhook(
                webhook_id=str(webhook.id),
                event_type=event_type,
                payload=payload,
                db=db
            )
            for webhook in matching_webhooks
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(
            f"Triggered {len(matching_webhooks)} webhooks: "
            f"{success_count} successful, {len(matching_webhooks) - success_count} failed"
        )
        
    except Exception as e:
        logger.error(f"Error triggering webhooks for event {event_type}: {str(e)}")
        
    finally:
        if close_db:
            await db.close()
