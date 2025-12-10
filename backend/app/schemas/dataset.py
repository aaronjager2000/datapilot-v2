"""
Dataset Pydantic schemas for request/response validation.
"""

from typing import Optional, Any
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, BaseDBSchema


# Column Information Schema
class ColumnInfo(BaseSchema):
    """Schema for column metadata in a dataset."""
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Data type (string, integer, float, boolean, date, etc.)")
    nullable: bool = Field(default=True, description="Whether the column allows null values")
    sample_values: list[Any] = Field(default_factory=list, description="Sample values from the column")
    unique_count: Optional[int] = Field(None, description="Number of unique values")
    null_count: Optional[int] = Field(None, description="Number of null values")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "age",
                "type": "integer",
                "nullable": True,
                "sample_values": [25, 30, 35, 40],
                "unique_count": 100,
                "null_count": 5
            }
        }
    }


# Base Dataset Schema
class DatasetBase(BaseSchema):
    """Base dataset schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")


# Dataset Create Schema
class DatasetCreate(DatasetBase):
    """Schema for creating a new dataset."""
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    file_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash")
    file_path: str = Field(..., description="Storage path or S3 key")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Sales Data Q4 2024",
                "description": "Quarterly sales report",
                "file_name": "sales_q4_2024.csv",
                "file_size": 1048576,
                "file_hash": "a" * 64,
                "file_path": "org-123/datasets/dataset-456/sales_q4_2024.csv"
            }
        }
    }


# Dataset Update Schema
class DatasetUpdate(BaseSchema):
    """Schema for updating dataset metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(uploading|processing|ready|failed)$")
    processing_error: Optional[str] = None
    row_count: Optional[int] = Field(None, ge=0)
    column_count: Optional[int] = Field(None, ge=0)
    schema_info: Optional[dict] = None


# Dataset in Database
class DatasetInDB(BaseDBSchema):
    """Full dataset representation from database."""
    organization_id: UUID
    name: str
    description: Optional[str]
    file_name: str
    file_size: int
    file_hash: str
    file_path: str
    status: str
    processing_error: Optional[str]
    row_count: Optional[int]
    column_count: Optional[int]
    schema_info: Optional[dict]
    created_by: Optional[UUID]


# Dataset Response Schema
class DatasetResponse(DatasetInDB):
    """Dataset response for API endpoints with full details."""
    file_size_mb: float = Field(..., description="File size in megabytes")
    columns: list[str] = Field(default_factory=list, description="Column names")

    @classmethod
    def from_orm(cls, dataset):
        """Create response from ORM model."""
        data = {
            "id": dataset.id,
            "organization_id": dataset.organization_id,
            "name": dataset.name,
            "description": dataset.description,
            "file_name": dataset.file_name,
            "file_size": dataset.file_size,
            "file_hash": dataset.file_hash,
            "file_path": dataset.file_path,
            "status": dataset.status.value if hasattr(dataset.status, 'value') else dataset.status,
            "processing_error": dataset.processing_error,
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "schema_info": dataset.schema_info,
            "created_by": dataset.created_by,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
            "file_size_mb": dataset.file_size_mb,
            "columns": []
        }

        # Extract column names from schema_info
        if dataset.schema_info and "columns" in dataset.schema_info:
            data["columns"] = dataset.schema_info["columns"]

        return cls(**data)


# Dataset List Item (Simplified)
class DatasetList(BaseSchema):
    """Simplified dataset schema for list views."""
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    file_name: str
    file_size_mb: float
    status: str
    row_count: Optional[int]
    column_count: Optional[int]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, dataset):
        """Create from ORM model."""
        return cls(
            id=dataset.id,
            organization_id=dataset.organization_id,
            name=dataset.name,
            description=dataset.description,
            file_name=dataset.file_name,
            file_size_mb=dataset.file_size_mb,
            status=dataset.status.value if hasattr(dataset.status, 'value') else dataset.status,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            created_by=dataset.created_by,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at
        )


# Dataset List Response
class DatasetListResponse(BaseSchema):
    """Response schema for list of datasets with pagination."""
    items: list[DatasetList] = Field(default_factory=list, description="List of datasets")
    total: int = Field(..., ge=0, description="Total number of datasets")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Maximum items per page")


# Dataset Preview Schema
class DatasetPreviewRecord(BaseSchema):
    """Single record in dataset preview."""
    row_number: int = Field(..., description="Row number")
    data: dict[str, Any] = Field(..., description="Row data")
    is_valid: bool = Field(True, description="Whether record passed validation")


class DatasetPreview(BaseSchema):
    """Dataset preview with sample records."""
    columns: list[str] = Field(default_factory=list, description="Column names")
    records: list[DatasetPreviewRecord] = Field(default_factory=list, description="Sample records")
    total_count: int = Field(..., ge=0, description="Total number of records in dataset")
    preview_count: int = Field(..., ge=0, description="Number of records in preview")

    model_config = {
        "json_schema_extra": {
            "example": {
                "columns": ["id", "name", "age", "email"],
                "records": [
                    {
                        "row_number": 1,
                        "data": {"id": 1, "name": "John Doe", "age": 30, "email": "john@example.com"},
                        "is_valid": True
                    },
                    {
                        "row_number": 2,
                        "data": {"id": 2, "name": "Jane Smith", "age": 25, "email": "jane@example.com"},
                        "is_valid": True
                    }
                ],
                "total_count": 1000,
                "preview_count": 2
            }
        }
    }


# Dataset Statistics
class DatasetStats(BaseSchema):
    """Dataset statistics and comprehensive metrics."""
    dataset_id: str = Field(..., description="Dataset ID")
    total_rows: Optional[int] = Field(None, ge=0, description="Total number of rows")
    total_columns: Optional[int] = Field(None, ge=0, description="Total number of columns")
    column_stats: dict[str, Any] = Field(default_factory=dict, description="Statistics for each column")

    model_config = {
        "json_schema_extra": {
            "example": {
                "dataset_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_rows": 1000,
                "total_columns": 5,
                "column_stats": {
                    "age": {
                        "min": 18,
                        "max": 65,
                        "mean": 35.5,
                        "null_count": 10,
                        "type_category": "numeric"
                    },
                    "name": {
                        "max_length": 50,
                        "unique_count": 980,
                        "null_count": 0,
                        "type_category": "string"
                    }
                }
            }
        }
    }


# Dataset Reprocess Request
class DatasetReprocessRequest(BaseSchema):
    """Request schema for reprocessing a dataset."""
    validation_rules: Optional[dict[str, Any]] = Field(None, description="Custom validation rules")
    cleaning_options: Optional[dict[str, Any]] = Field(None, description="Data cleaning options")
    normalization_options: Optional[dict[str, Any]] = Field(None, description="Normalization options")

    model_config = {
        "json_schema_extra": {
            "example": {
                "validation_rules": {
                    "required_columns": ["id", "name"],
                    "data_types": {
                        "id": "integer",
                        "age": "integer"
                    }
                },
                "cleaning_options": {
                    "remove_duplicates": True,
                    "handle_missing": "drop"
                },
                "normalization_options": {
                    "normalize_column_names": True,
                    "case": "snake"
                }
            }
        }
    }
