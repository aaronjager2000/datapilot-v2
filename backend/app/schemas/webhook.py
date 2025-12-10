"""
Webhook Pydantic schemas for API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, validator


class WebhookBase(BaseModel):
    """Base webhook schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Webhook name")
    url: str = Field(..., description="Destination URL for webhook POST requests")
    events: List[str] = Field(default_factory=list, description="Event types to trigger webhook")
    is_active: bool = Field(default=True, description="Whether webhook is active")


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook."""
    
    retry_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Retry configuration (max_attempts, backoff_strategy, etc.)"
    )
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @validator('events')
    def validate_events(cls, v):
        """Validate event types."""
        valid_events = {
            'dataset.created',
            'dataset.processing',
            'dataset.processed',
            'dataset.failed',
            'dataset.updated',
            'dataset.deleted',
            'insight.generated',
            'visualization.created',
            'dashboard.created',
            'record.created',
            'record.updated',
            'record.deleted',
        }
        
        for event in v:
            if event not in valid_events:
                raise ValueError(
                    f'Invalid event type: {event}. '
                    f'Valid events: {", ".join(sorted(valid_events))}'
                )
        
        return v


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    retry_config: Optional[Dict[str, Any]] = None
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if v is not None and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @validator('events')
    def validate_events(cls, v):
        """Validate event types."""
        if v is None:
            return v
            
        valid_events = {
            'dataset.created',
            'dataset.processing',
            'dataset.processed',
            'dataset.failed',
            'dataset.updated',
            'dataset.deleted',
            'insight.generated',
            'visualization.created',
            'dashboard.created',
            'record.created',
            'record.updated',
            'record.deleted',
        }
        
        for event in v:
            if event not in valid_events:
                raise ValueError(
                    f'Invalid event type: {event}. '
                    f'Valid events: {", ".join(sorted(valid_events))}'
                )
        
        return v


class WebhookResponse(WebhookBase):
    """Schema for webhook response."""
    
    id: UUID
    organization_id: UUID
    secret: str = Field(..., description="Webhook secret for signature verification")
    retry_config: Dict[str, Any]
    last_triggered: Optional[datetime] = None
    failure_count: int = Field(default=0, description="Consecutive failure count")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Schema for webhook list response."""
    
    webhooks: List[WebhookResponse]
    total: int


class WebhookLogResponse(BaseModel):
    """Schema for webhook log response."""
    
    id: UUID
    webhook_id: UUID
    event_type: str
    payload: Dict[str, Any]
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    attempt: int
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    
    # Computed properties
    was_successful: bool = Field(default=False, description="Whether delivery was successful")
    status_category: str = Field(default="unknown", description="Status category")
    
    class Config:
        from_attributes = True


class WebhookLogListResponse(BaseModel):
    """Schema for webhook log list response."""
    
    logs: List[WebhookLogResponse]
    total: int


class WebhookWithLogsResponse(WebhookResponse):
    """Schema for webhook with recent logs."""
    
    recent_logs: List[WebhookLogResponse] = Field(default_factory=list)


class WebhookTestRequest(BaseModel):
    """Schema for testing a webhook."""
    
    event_type: Optional[str] = Field(
        default="test.event",
        description="Event type to use for test"
    )
    payload: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"test": True, "message": "This is a test webhook"},
        description="Test payload to send"
    )


class WebhookTestResponse(BaseModel):
    """Schema for webhook test response."""
    
    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class InboundWebhookResponse(BaseModel):
    """Schema for inbound webhook response."""
    
    success: bool
    message: str
    dataset_id: Optional[UUID] = None
