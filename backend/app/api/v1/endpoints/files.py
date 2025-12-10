"""
File upload and management endpoints.
"""

import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.file import File as FileModel, StorageLocation
from app.models.dataset import Dataset, DatasetStatus
from app.models.organization import Organization
from app.schemas.file import FileUploadResponse, FileResponse, FileWithURL, FileListResponse
from app.utils.file_handler import (
    save_upload_file,
    get_file_hash,
    get_file_metadata,
    validate_file_type,
    cleanup_temp_files
)
from app.utils.s3_client import S3Client

logger = logging.getLogger(__name__)

router = APIRouter()

# File upload constraints
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls"]
ALLOWED_MIME_TYPES = [
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
]


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a data file (CSV or Excel).

    - Validates file type and size
    - Checks organization storage limits
    - Saves file temporarily
    - Uploads to S3/R2
    - Creates File and Dataset records
    - Returns dataset_id for tracking processing status
    """
    try:
        # Validate file size (check content-length header first)
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )

        # Save file temporarily
        temp_file_path = await save_upload_file(
            file,
            organization_id=str(current_user.organization_id),
            subfolder="uploads"
        )

        # Get file metadata
        file_metadata = get_file_metadata(temp_file_path)

        # Validate file size again (actual size)
        if file_metadata["size"] > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )

        # Validate file type
        if not validate_file_type(
            temp_file_path,
            allowed_types=ALLOWED_MIME_TYPES,
            allowed_extensions=ALLOWED_EXTENSIONS
        ):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Calculate file hash for deduplication
        file_hash = get_file_hash(temp_file_path)

        # Check for duplicate file (same hash in same organization)
        duplicate_query = select(FileModel).where(
            FileModel.organization_id == current_user.organization_id,
            FileModel.file_hash == file_hash
        )
        result = await db.execute(duplicate_query)
        existing_file = result.scalar_one_or_none()

        if existing_file:
            logger.info(f"Duplicate file detected: {file_hash}")
            # Return existing dataset if file was already uploaded
            if existing_file.dataset_id:
                dataset_query = select(Dataset).where(Dataset.id == existing_file.dataset_id)
                dataset_result = await db.execute(dataset_query)
                existing_dataset = dataset_result.scalar_one_or_none()

                if existing_dataset:
                    return FileUploadResponse(
                        file_id=existing_file.id,
                        dataset_id=existing_dataset.id,
                        file_name=existing_file.file_name,
                        file_size=existing_file.file_size,
                        file_size_mb=existing_file.file_size_mb,
                        status=existing_dataset.status.value,
                        message="This file has already been uploaded"
                    )

        # Check organization storage limits
        org_query = select(Organization).where(Organization.id == current_user.organization_id)
        org_result = await db.execute(org_query)
        organization = org_result.scalar_one_or_none()

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Calculate current storage usage
        storage_query = select(func.sum(FileModel.file_size)).where(
            FileModel.organization_id == current_user.organization_id
        )
        storage_result = await db.execute(storage_query)
        current_storage_bytes = storage_result.scalar() or 0
        current_storage_gb = current_storage_bytes / (1024 ** 3)

        # Check if adding this file would exceed storage limit
        new_storage_gb = (current_storage_bytes + file_metadata["size"]) / (1024 ** 3)
        if new_storage_gb > organization.max_storage_gb:
            raise HTTPException(
                status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                detail=f"Storage limit exceeded. Current: {current_storage_gb:.2f}GB, Limit: {organization.max_storage_gb}GB"
            )

        # Upload to S3/R2 if configured
        storage_location = StorageLocation.LOCAL
        s3_key = None

        if settings.STORAGE_TYPE in ["s3", "r2"]:
            s3_client = S3Client()
            s3_key = s3_client.build_key(
                organization_id=str(current_user.organization_id),
                dataset_id="temp",  # Will update after dataset is created
                filename=file_metadata["filename"]
            )

            upload_success = await s3_client.upload_file(
                file_path=temp_file_path,
                key=s3_key,
                content_type=file_metadata["mime_type"]
            )

            if upload_success:
                storage_location = StorageLocation.S3 if settings.STORAGE_TYPE == "s3" else StorageLocation.R2
                logger.info(f"File uploaded to {storage_location.value}: {s3_key}")
            else:
                logger.warning(f"Failed to upload to {settings.STORAGE_TYPE}, using local storage")

        # Create File record
        file_record = FileModel(
            organization_id=current_user.organization_id,
            uploaded_by=current_user.id,
            file_name=file_metadata["filename"],
            file_size=file_metadata["size"],
            file_hash=file_hash,
            file_path=s3_key if s3_key else temp_file_path,
            mime_type=file_metadata["mime_type"],
            storage_location=storage_location
        )
        db.add(file_record)
        await db.flush()  # Get file_record.id

        # Create Dataset record with status="processing"
        dataset = Dataset(
            organization_id=current_user.organization_id,
            name=file_metadata["filename"].rsplit(".", 1)[0],  # Remove extension
            description=f"Dataset created from {file_metadata['filename']}",
            file_name=file_metadata["filename"],
            file_size=file_metadata["size"],
            file_hash=file_hash,
            file_path=s3_key if s3_key else temp_file_path,
            status=DatasetStatus.PROCESSING,
            created_by=current_user.id
        )
        db.add(dataset)
        await db.flush()  # Get dataset.id

        # Link file to dataset
        file_record.dataset_id = dataset.id

        await db.commit()
        await db.refresh(file_record)
        await db.refresh(dataset)

        logger.info(f"File uploaded successfully: {file_record.id}, dataset: {dataset.id}")

        # TODO: Enqueue background task for parsing the file
        # This will be implemented in the next step with the parser service

        return FileUploadResponse(
            file_id=file_record.id,
            dataset_id=dataset.id,
            file_name=file_record.file_name,
            file_size=file_record.file_size,
            file_size_mb=file_record.file_size_mb,
            status=dataset.status.value,
            message="File uploaded successfully and is being processed"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/{file_id}", response_model=FileWithURL)
async def get_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get file metadata and generate presigned download URL.

    Returns file information with a temporary download URL (expires in 1 hour).
    """
    # Get file record
    query = select(FileModel).where(
        FileModel.id == file_id,
        FileModel.organization_id == current_user.organization_id
    )
    result = await db.execute(query)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Generate presigned URL if file is in S3/R2
    download_url = None
    url_expires_in = None

    if file_record.storage_location in [StorageLocation.S3, StorageLocation.R2]:
        s3_client = S3Client()
        download_url = await s3_client.generate_presigned_url(
            key=file_record.file_path,
            expiration=3600  # 1 hour
        )
        url_expires_in = 3600

    # Create response
    response_data = FileResponse.from_orm(file_record)

    return FileWithURL(
        **response_data.model_dump(),
        download_url=download_url,
        url_expires_in=url_expires_in
    )


@router.get("/", response_model=FileListResponse)
async def list_files(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all files for the current organization.

    Returns paginated list of files with metadata.
    """
    # Get total count
    count_query = select(func.count(FileModel.id)).where(
        FileModel.organization_id == current_user.organization_id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get files
    query = select(FileModel).where(
        FileModel.organization_id == current_user.organization_id
    ).order_by(FileModel.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    files = result.scalars().all()

    return FileListResponse(
        total=total,
        skip=skip,
        limit=limit,
        files=[FileResponse.from_orm(f) for f in files],
        has_more=(skip + limit) < total
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a file and its associated dataset.

    This will also delete all records associated with the dataset due to cascade rules.
    """
    # Get file record
    query = select(FileModel).where(
        FileModel.id == file_id,
        FileModel.organization_id == current_user.organization_id
    )
    result = await db.execute(query)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    try:
        # Delete from S3/R2 if applicable
        if file_record.storage_location in [StorageLocation.S3, StorageLocation.R2]:
            s3_client = S3Client()
            await s3_client.delete_file(file_record.file_path)
            logger.info(f"Deleted file from {file_record.storage_location.value}: {file_record.file_path}")

        # Delete file record (will cascade to dataset and records)
        await db.delete(file_record)
        await db.commit()

        logger.info(f"File deleted successfully: {file_id}")

    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )
