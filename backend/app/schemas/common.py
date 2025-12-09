"""
Common Pydantic schemas used across the application.

These base schemas provide common patterns for request/response validation.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.

    Uses Pydantic v2 ConfigDict for configuration.
    """
    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode (was orm_mode in v1)
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """Schema with ID field."""
    id: UUID


class BaseDBSchema(IDSchema, TimestampSchema):
    """
    Base schema for database models.

    Includes id, created_at, and updated_at fields.
    """
    pass


class MessageResponse(BaseSchema):
    """Generic message response."""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseSchema):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    field: Optional[str] = None


class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints."""
    skip: int = 0
    limit: int = 100

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "skip": 0,
                "limit": 100
            }
        }
    )


class PaginatedResponse(BaseSchema):
    """Generic paginated response."""
    total: int
    skip: int
    limit: int
    items: list
