"""
Record Pydantic schemas for request/response validation.
"""

from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import Field

from app.schemas.common import BaseSchema, BaseDBSchema


# Filter Operators
class FilterOperator(str, Enum):
    """Operators for filtering records."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


# Sort Direction
class SortDirection(str, Enum):
    """Sort direction for record queries."""
    ASC = "asc"
    DESC = "desc"


# Base Record Schema
class RecordBase(BaseSchema):
    """Base record schema with data field."""
    data: dict[str, Any] = Field(..., description="Key-value pairs for each column")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": {
                    "name": "John Doe",
                    "age": 30,
                    "email": "john@example.com"
                }
            }
        }
    }


# Record Create Schema
class RecordCreate(RecordBase):
    """Schema for creating a new record."""
    dataset_id: UUID
    row_number: int = Field(..., ge=1, description="Row number in original file")
    is_valid: bool = Field(default=True)
    validation_errors: Optional[list[str]] = None


# Bulk Record Create
class BulkRecordCreate(BaseSchema):
    """Schema for bulk record insertion."""
    dataset_id: UUID
    records: list[RecordCreate] = Field(..., min_length=1, max_length=10000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
                "records": [
                    {
                        "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
                        "row_number": 1,
                        "data": {"name": "Alice", "age": 25},
                        "is_valid": True
                    },
                    {
                        "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
                        "row_number": 2,
                        "data": {"name": "Bob", "age": 30},
                        "is_valid": True
                    }
                ]
            }
        }
    }


# Record in Database
class RecordInDB(BaseDBSchema):
    """Full record representation from database."""
    organization_id: UUID
    dataset_id: UUID
    row_number: int
    data: dict[str, Any]
    is_valid: bool
    validation_errors: Optional[list[str]]


# Record Response Schema
class RecordResponse(RecordInDB):
    """Record response for API endpoints."""
    
    @classmethod
    def from_orm(cls, record):
        """Create from ORM model."""
        return cls(
            id=record.id,
            organization_id=record.organization_id,
            dataset_id=record.dataset_id,
            row_number=record.row_number,
            data=record.data,
            is_valid=record.is_valid,
            validation_errors=record.validation_errors,
            created_at=record.created_at,
            updated_at=record.updated_at
        )


# Record Filter
class RecordFilter(BaseSchema):
    """Filter for querying records."""
    column: str = Field(..., description="Column name to filter on")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Optional[Any] = Field(None, description="Value to filter by (not needed for is_null/is_not_null)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "column": "age",
                    "operator": "gte",
                    "value": 18
                },
                {
                    "column": "name",
                    "operator": "contains",
                    "value": "John"
                },
                {
                    "column": "email",
                    "operator": "is_not_null"
                }
            ]
        }
    }


# Sort Configuration
class RecordSort(BaseSchema):
    """Sort configuration for record queries."""
    column: str = Field(..., description="Column name to sort by")
    direction: SortDirection = Field(default=SortDirection.ASC, description="Sort direction")

    model_config = {
        "json_schema_extra": {
            "example": {
                "column": "created_at",
                "direction": "desc"
            }
        }
    }


# Record Query Parameters
class RecordQuery(BaseSchema):
    """Query parameters for fetching records."""
    dataset_id: UUID = Field(..., description="Dataset to query records from")
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum records to return")
    filters: list[RecordFilter] = Field(default_factory=list, description="Filters to apply")
    sort: Optional[RecordSort] = Field(None, description="Sort configuration")
    only_valid: Optional[bool] = Field(None, description="Filter by validation status")
    search: Optional[str] = Field(None, description="Search across all text fields")

    model_config = {
        "json_schema_extra": {
            "example": {
                "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
                "skip": 0,
                "limit": 100,
                "filters": [
                    {
                        "column": "age",
                        "operator": "gte",
                        "value": 18
                    }
                ],
                "sort": {
                    "column": "name",
                    "direction": "asc"
                },
                "only_valid": True,
                "search": "john"
            }
        }
    }


# Record List Response
class RecordListResponse(BaseSchema):
    """Paginated response for record queries."""
    total: int = Field(..., description="Total number of matching records")
    skip: int
    limit: int
    records: list[RecordResponse]
    has_more: bool = Field(..., description="Whether there are more records")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 1000,
                "skip": 0,
                "limit": 100,
                "records": [],
                "has_more": True
            }
        }
    }


# Record Stats
class RecordStats(BaseSchema):
    """Statistics about records in a dataset."""
    dataset_id: UUID
    total_records: int = Field(..., ge=0)
    valid_records: int = Field(..., ge=0)
    invalid_records: int = Field(..., ge=0)
    validation_rate: float = Field(..., ge=0, le=100, description="Percentage of valid records")

    @classmethod
    def calculate(cls, dataset_id: UUID, total: int, valid: int):
        """Calculate stats from counts."""
        invalid = total - valid
        rate = (valid / total * 100) if total > 0 else 100.0
        return cls(
            dataset_id=dataset_id,
            total_records=total,
            valid_records=valid,
            invalid_records=invalid,
            validation_rate=round(rate, 2)
        )
