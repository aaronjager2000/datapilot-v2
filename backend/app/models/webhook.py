"""
Webhook models - webhook configuration and delivery tracking.

Webhooks allow external systems to be notified of events in DataPilot,
such as dataset processing, insight generation, or data updates.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime
import secrets

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization


class Webhook(BaseModel):
    """
    Webhook model - configuration for event notifications.

    Webhooks trigger HTTP POST requests to external URLs when specific
    events occur, enabling integrations with external systems.
    """

    __tablename__ = "webhooks"

    # Organization Reference
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization this webhook belongs to"
    )

    # Webhook Configuration
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Descriptive name for this webhook"
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Destination URL for webhook POSTs"
    )

    secret: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Secret key for HMAC signature verification"
    )

    # Event Configuration
    events: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of event types that trigger this webhook"
    )
    """
    Supported events:
    - dataset.created: New dataset uploaded
    - dataset.processing: Dataset processing started
    - dataset.processed: Dataset processing completed
    - dataset.failed: Dataset processing failed
    - dataset.updated: Dataset metadata updated
    - dataset.deleted: Dataset deleted
    - insight.generated: New insights generated
    - visualization.created: New visualization created
    - dashboard.created: New dashboard created
    - record.created: New record added
    - record.updated: Record updated
    - record.deleted: Record deleted
    """

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this webhook is active"
    )

    # Retry Configuration
    retry_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Retry configuration (max_attempts, backoff_strategy, timeout)"
    )
    """
    Default retry config:
    {
        "max_attempts": 3,
        "backoff_strategy": "exponential",  # linear, exponential, constant
        "initial_delay": 60,  # seconds
        "max_delay": 3600,  # seconds
        "timeout": 30  # request timeout in seconds
    }
    """

    # Tracking
    last_triggered: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Last time this webhook was triggered"
    )

    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Consecutive failure count (reset on success)"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        foreign_keys=[organization_id],
        back_populates="webhooks"
    )

    logs: Mapped[list["WebhookLog"]] = relationship(
        "WebhookLog",
        back_populates="webhook",
        cascade="all, delete-orphan",
        order_by="WebhookLog.created_at.desc()"
    )

    # Indexes
    __table_args__ = (
        Index("ix_webhooks_org_active", "organization_id", "is_active"),
        {"comment": "Webhook table for multi-tenant event notifications"},
    )

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, name={self.name}, url={self.url[:50]}, is_active={self.is_active})>"

    @classmethod
    def generate_secret(cls) -> str:
        """
        Generate a cryptographically secure webhook secret.

        Returns:
            64-character hex secret
        """
        return secrets.token_hex(32)

    @property
    def is_healthy(self) -> bool:
        """Check if webhook is healthy (low failure count)."""
        max_failures = self.retry_config.get("max_consecutive_failures", 10)
        return self.failure_count < max_failures

    @property
    def should_auto_disable(self) -> bool:
        """Check if webhook should be auto-disabled due to failures."""
        max_failures = self.retry_config.get("auto_disable_after", 20)
        return self.failure_count >= max_failures

    def increment_failure_count(self):
        """Increment failure count."""
        self.failure_count += 1

    def reset_failure_count(self):
        """Reset failure count to zero (called on successful delivery)."""
        self.failure_count = 0

    def update_last_triggered(self):
        """Update last triggered timestamp to now."""
        from datetime import datetime
        self.last_triggered = datetime.utcnow()

    def has_event(self, event_type: str) -> bool:
        """
        Check if webhook is configured for a specific event type.

        Args:
            event_type: Event type to check (e.g., "dataset.processed")

        Returns:
            True if webhook listens for this event
        """
        if not self.events:
            return False
        return event_type in self.events

    def add_event(self, event_type: str):
        """
        Add an event type to the webhook.

        Args:
            event_type: Event type to add
        """
        if not self.events:
            self.events = []
        if event_type not in self.events:
            self.events.append(event_type)

    def remove_event(self, event_type: str):
        """
        Remove an event type from the webhook.

        Args:
            event_type: Event type to remove
        """
        if self.events and event_type in self.events:
            self.events.remove(event_type)

    def get_retry_config(self, key: str, default=None):
        """
        Get a retry configuration value.

        Args:
            key: Config key
            default: Default value if key doesn't exist

        Returns:
            Config value or default
        """
        return self.retry_config.get(key, default)

    def set_retry_config(self, key: str, value):
        """
        Set a retry configuration value.

        Args:
            key: Config key
            value: Value to set
        """
        if self.retry_config is None:
            self.retry_config = {}
        self.retry_config[key] = value

    @classmethod
    def get_default_retry_config(cls) -> dict:
        """
        Get default retry configuration.

        Returns:
            Default retry config dict
        """
        return {
            "max_attempts": 3,
            "backoff_strategy": "exponential",
            "initial_delay": 60,
            "max_delay": 3600,
            "timeout": 30,
            "max_consecutive_failures": 10,
            "auto_disable_after": 20
        }


class WebhookLog(BaseModel):
    """
    WebhookLog model - tracks individual webhook delivery attempts.

    Logs every attempt to deliver a webhook, including retries,
    for debugging and monitoring purposes.
    """

    __tablename__ = "webhook_logs"

    # Webhook Reference
    webhook_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Webhook that was triggered"
    )

    # Event Information
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of event that triggered this webhook"
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Webhook payload (event data)"
    )

    # Delivery Information
    response_status: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="HTTP response status code (null if request failed)"
    )

    response_body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="HTTP response body (truncated to 10KB)"
    )

    attempt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Delivery attempt number (1 for first attempt, 2+ for retries)"
    )

    # Error Information
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if delivery failed"
    )

    # Timing
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Request duration in milliseconds"
    )

    # Relationships
    webhook: Mapped["Webhook"] = relationship(
        "Webhook",
        foreign_keys=[webhook_id],
        back_populates="logs"
    )

    # Indexes
    __table_args__ = (
        Index("ix_webhook_logs_webhook_event", "webhook_id", "event_type"),
        Index("ix_webhook_logs_created", "created_at"),
        Index("ix_webhook_logs_status", "response_status"),
        {"comment": "Webhook delivery log table"},
    )

    def __repr__(self) -> str:
        return f"<WebhookLog(id={self.id}, webhook_id={self.webhook_id}, event={self.event_type}, status={self.response_status}, attempt={self.attempt})>"

    @property
    def was_successful(self) -> bool:
        """Check if delivery was successful (2xx status code)."""
        return self.response_status is not None and 200 <= self.response_status < 300

    @property
    def was_client_error(self) -> bool:
        """Check if delivery failed with client error (4xx)."""
        return self.response_status is not None and 400 <= self.response_status < 500

    @property
    def was_server_error(self) -> bool:
        """Check if delivery failed with server error (5xx)."""
        return self.response_status is not None and 500 <= self.response_status < 600

    @property
    def should_retry(self) -> bool:
        """Check if this delivery should be retried (5xx or network error)."""
        if self.was_successful:
            return False
        if self.was_client_error:
            return False  # Don't retry client errors
        return True  # Retry server errors and network failures

    @property
    def status_category(self) -> str:
        """Get human-readable status category."""
        if self.was_successful:
            return "success"
        elif self.was_client_error:
            return "client_error"
        elif self.was_server_error:
            return "server_error"
        else:
            return "network_error"

    def truncate_response_body(self, max_length: int = 10000):
        """
        Truncate response body to maximum length.

        Args:
            max_length: Maximum length in characters
        """
        if self.response_body and len(self.response_body) > max_length:
            self.response_body = self.response_body[:max_length] + "... (truncated)"

    @classmethod
    def create_from_delivery(
        cls,
        webhook_id: UUID,
        event_type: str,
        payload: dict,
        response_status: Optional[int],
        response_body: Optional[str],
        attempt: int,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> "WebhookLog":
        """
        Factory method to create a webhook log from delivery result.

        Args:
            webhook_id: Webhook ID
            event_type: Event type
            payload: Webhook payload
            response_status: HTTP status code
            response_body: HTTP response body
            attempt: Attempt number
            error_message: Optional error message
            duration_ms: Request duration in milliseconds

        Returns:
            New WebhookLog instance
        """
        log = cls(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            response_status=response_status,
            response_body=response_body,
            attempt=attempt,
            error_message=error_message,
            duration_ms=duration_ms
        )

        # Truncate response body if too long
        log.truncate_response_body()

        return log
