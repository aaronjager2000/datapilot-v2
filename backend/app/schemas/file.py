"""
File Pydantic schemas for request/response validation.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, BaseDBSchema


# File Upload Response
class FileUploadResponse(BaseSchema):
    """Response after successful file upload."""
    file_id: UUID = Field(..., description="ID of the uploaded file")
    dataset_id: UUID = Field(..., description="ID of the created dataset")
    file_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in megabytes")
    status: str = Field(..., description="Processing status (uploading/processing)")
    message: str = Field(..., description="Status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "dataset_id": "123e4567-e89b-12d3-a456-426614174001",
                "file_name": "sales_data.csv",
                "file_size": 1048576,
                "file_size_mb": 1.0,
                "status": "processing",
                "message": "File uploaded successfully and is being processed"
            }
        }
    }


# File in Database
class FileInDB(BaseDBSchema):
    """Full file representation from database."""
    organization_id: UUID
    uploaded_by: Optional[UUID]
    file_name: str
    file_size: int
    file_hash: str
    file_path: str
    mime_type: str
    storage_location: str
    dataset_id: Optional[UUID]


# File Response Schema
class FileResponse(FileInDB):
    """File response for API endpoints."""
    file_size_mb: float = Field(..., description="File size in megabytes")
    is_processed: bool = Field(..., description="Whether file has been processed into a dataset")

    @classmethod
    def from_orm(cls, file_obj):
        """Create response from ORM model."""
        return cls(
            id=file_obj.id,
            organization_id=file_obj.organization_id,
            uploaded_by=file_obj.uploaded_by,
            file_name=file_obj.file_name,
            file_size=file_obj.file_size,
            file_hash=file_obj.file_hash,
            file_path=file_obj.file_path,
            mime_type=file_obj.mime_type,
            storage_location=file_obj.storage_location.value if hasattr(file_obj.storage_location, 'value') else file_obj.storage_location,
            dataset_id=file_obj.dataset_id,
            created_at=file_obj.created_at,
            updated_at=file_obj.updated_at,
            file_size_mb=file_obj.file_size_mb,
            is_processed=file_obj.is_processed
        )


# File with Download URL
class FileWithURL(FileResponse):
    """File response with presigned download URL."""
    download_url: Optional[str] = Field(None, description="Presigned URL for downloading the file")
    url_expires_in: Optional[int] = Field(None, description="URL expiration time in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "file_name": "sales_data.csv",
                "file_size_mb": 1.0,
                "download_url": "https://s3.amazonaws.com/bucket/file?signature=...",
                "url_expires_in": 3600
            }
        }
    }


# File List Response
class FileListResponse(BaseSchema):
    """Paginated response for file queries."""
    total: int = Field(..., description="Total number of files")
    skip: int
    limit: int
    files: list[FileResponse]
    has_more: bool = Field(..., description="Whether there are more files")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 50,
                "skip": 0,
                "limit": 20,
                "files": [],
                "has_more": True
            }
        }
    }
