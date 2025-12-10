"""
Dataset API endpoints.

Handles dataset upload, retrieval, updates, deletion, preview, statistics,
and reprocessing with proper authentication and permissions.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.tenant import get_current_organization_id
from app.api.v1.dependencies.permissions import require_permission
from app.models.user import User
from app.models.dataset import DatasetStatus
from app.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    DatasetListResponse,
    DatasetUpdate,
    DatasetPreview,
    DatasetStats,
    DatasetReprocessRequest
)
from app.schemas.common import PaginationParams
from app.services.dataset import (
    create_dataset,
    get_dataset,
    list_datasets,
    update_dataset,
    delete_dataset,
    get_dataset_preview,
    get_dataset_stats,
    reprocess_dataset,
    DatasetNotFoundError,
    DatasetServiceError
)
from app.utils.s3_client import S3Client
from app.utils.webhook import trigger_webhooks_for_event
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("data:import"))]
)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Query(None, description="Dataset name"),
    description: Optional[str] = Query(None, description="Dataset description"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Upload file and create dataset.
    
    Accepts CSV or Excel files and triggers background processing.
    
    **Required Permission:** `data:import`
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
        
        file_ext = file.filename.rsplit('.', 1)[-1].lower()
        allowed_extensions = ['csv', 'xlsx', 'xls']
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Prepare metadata
        metadata = {
            'name': name or file.filename,
            'description': description
        }
        
        # Create dataset
        dataset = await create_dataset(
            db=db,
            file=file,
            metadata=metadata,
            user=current_user,
            organization_id=organization_id
        )
        
        logger.info(f"User {current_user.id} uploaded dataset {dataset.id}")
        
        # Trigger webhook for dataset.created event
        if background_tasks:
            background_tasks.add_task(
                trigger_webhooks_for_event,
                event_type="dataset.created",
                payload={
                    "dataset_id": str(dataset.id),
                    "name": dataset.name,
                    "status": dataset.status.value if dataset.status else None,
                    "created_by": str(current_user.id),
                    "file_name": file.filename,
                },
                organization_id=str(organization_id),
                db=None  # Will create new session
            )
        
        return DatasetResponse.from_orm(dataset)
    
    except DatasetServiceError as e:
        logger.error(f"Failed to upload dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "",
    response_model=DatasetListResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def list_organization_datasets(
    status_filter: Optional[DatasetStatus] = Query(None, alias="status", description="Filter by status"),
    created_by: Optional[UUID] = Query(None, description="Filter by creator user ID"),
    date_from: Optional[str] = Query(None, description="Filter by creation date (from)"),
    date_to: Optional[str] = Query(None, description="Filter by creation date (to)"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    List all datasets for the organization.
    
    Supports filtering by status, creator, date range, and search.
    Results are paginated.
    
    **Required Permission:** `data:view`
    """
    try:
        # Build filters
        filters = {}
        
        if status_filter:
            filters['status'] = status_filter
        
        if created_by:
            filters['created_by'] = created_by
        
        if date_from:
            filters['date_from'] = date_from
        
        if date_to:
            filters['date_to'] = date_to
        
        if search:
            filters['search'] = search
        
        # Get datasets
        datasets, total = await list_datasets(
            db=db,
            organization_id=organization_id,
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        return DatasetListResponse(
            items=[DatasetResponse.from_orm(ds) for ds in datasets],
            total=total,
            skip=skip,
            limit=limit
        )
    
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve datasets"
        )


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_dataset_details(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get dataset details with full schema information.
    
    Includes processing status, errors, and complete schema metadata.
    
    **Required Permission:** `data:view`
    """
    try:
        dataset = await get_dataset(db, dataset_id, organization_id)
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        return DatasetResponse.from_orm(dataset)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dataset"
        )


@router.put(
    "/{dataset_id}",
    response_model=DatasetResponse,
    dependencies=[Depends(require_permission("data:edit"))]
)
async def update_dataset_metadata(
    dataset_id: UUID,
    updates: DatasetUpdate,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Update dataset metadata (name, description).
    
    Only metadata can be updated; data reprocessing requires the reprocess endpoint.
    
    **Required Permission:** `data:edit`
    """
    try:
        updated_dataset = await update_dataset(
            db=db,
            dataset_id=dataset_id,
            organization_id=organization_id,
            updates=updates.dict(exclude_unset=True)
        )
        
        logger.info(f"User {current_user.id} updated dataset {dataset_id}")
        
        # Trigger webhook for dataset.updated event
        if background_tasks:
            background_tasks.add_task(
                trigger_webhooks_for_event,
                event_type="dataset.updated",
                payload={
                    "dataset_id": str(dataset_id),
                    "name": updated_dataset.name,
                    "updated_by": str(current_user.id),
                    "changes": updates.dict(exclude_unset=True),
                },
                organization_id=str(organization_id),
                db=None  # Will create new session
            )
        
        return DatasetResponse.from_orm(updated_dataset)
    
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to update dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update dataset"
        )


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("data:delete"))]
)
async def delete_dataset_endpoint(
    dataset_id: UUID,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Soft delete dataset.
    
    Marks the dataset as deleted without removing data from the database.
    Associated records are also soft-deleted.
    
    **Required Permission:** `data:delete`
    """
    try:
        # Get dataset info before deletion for webhook payload
        dataset = await get_dataset(db, dataset_id, organization_id)
        dataset_name = dataset.name if dataset else None
        
        await delete_dataset(db, dataset_id, organization_id)
        
        logger.info(f"User {current_user.id} deleted dataset {dataset_id}")
        
        # Trigger webhook for dataset.deleted event
        if background_tasks:
            background_tasks.add_task(
                trigger_webhooks_for_event,
                event_type="dataset.deleted",
                payload={
                    "dataset_id": str(dataset_id),
                    "name": dataset_name,
                    "deleted_by": str(current_user.id),
                },
                organization_id=str(organization_id),
                db=None  # Will create new session
            )
        
        return None
    
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to delete dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset"
        )


@router.get(
    "/{dataset_id}/preview",
    response_model=DatasetPreview,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_dataset_preview_endpoint(
    dataset_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Number of records to preview"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get preview of dataset records.
    
    Returns the first N records with column headers and types.
    Useful for quick inspection before running queries.
    
    **Required Permission:** `data:view`
    """
    try:
        preview_data = await get_dataset_preview(
            db=db,
            dataset_id=dataset_id,
            organization_id=organization_id,
            limit=limit
        )
        
        return DatasetPreview(**preview_data)
    
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to get dataset preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preview"
        )


@router.get(
    "/{dataset_id}/stats",
    response_model=DatasetStats,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_dataset_statistics(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get statistics for all columns in the dataset.
    
    Returns comprehensive statistics including:
    - Null counts
    - Unique values
    - Distributions
    - Data types
    - Min/max values (for numeric columns)
    
    **Required Permission:** `data:view`
    """
    try:
        stats = await get_dataset_stats(
            db=db,
            dataset_id=dataset_id,
            organization_id=organization_id
        )
        
        return DatasetStats(**stats)
    
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to get dataset stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@router.post(
    "/{dataset_id}/reprocess",
    response_model=DatasetResponse,
    dependencies=[Depends(require_permission("data:import"))]
)
async def reprocess_dataset_endpoint(
    dataset_id: UUID,
    settings: Optional[DatasetReprocessRequest] = Body(None),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Re-run ingestion pipeline with new settings.
    
    Deletes existing records and reprocesses the original file.
    Useful for applying new transformations or fixing processing errors.
    
    **Required Permission:** `data:import`
    """
    try:
        reprocess_settings = settings.dict() if settings else None
        
        dataset = await reprocess_dataset(
            db=db,
            dataset_id=dataset_id,
            organization_id=organization_id,
            settings=reprocess_settings
        )
        
        logger.info(f"User {current_user.id} triggered reprocessing for dataset {dataset_id}")
        
        # Trigger webhook for dataset.processing event
        if background_tasks:
            background_tasks.add_task(
                trigger_webhooks_for_event,
                event_type="dataset.processing",
                payload={
                    "dataset_id": str(dataset.id),
                    "name": dataset.name,
                    "status": dataset.status.value if dataset.status else None,
                    "triggered_by": str(current_user.id),
                    "settings": reprocess_settings,
                },
                organization_id=str(organization_id),
                db=None  # Will create new session
            )
        
        return DatasetResponse.from_orm(dataset)
    
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to reprocess dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reprocess dataset"
        )


@router.get(
    "/{dataset_id}/download",
    dependencies=[Depends(require_permission("data:export"))]
)
async def download_dataset(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Generate presigned URL for downloading the original file.
    
    For S3 storage, returns a temporary download URL.
    For local storage, returns the file path.
    
    **Required Permission:** `data:export`
    """
    try:
        dataset = await get_dataset(db, dataset_id, organization_id)
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        # Generate download URL based on storage type
        if settings.STORAGE_TYPE in ["s3", "r2"]:
            # Generate presigned URL for S3
            s3_client = S3Client()
            download_url = s3_client.generate_presigned_url(
                dataset.file_path,
                expiration=3600  # 1 hour
            )
            
            logger.info(f"Generated download URL for dataset {dataset_id}")
            
            return {
                "download_url": download_url,
                "expires_in": 3600,
                "filename": dataset.file_name
            }
        else:
            # For local storage, return file info
            return {
                "file_path": dataset.file_path,
                "filename": dataset.file_name,
                "message": "Local storage - file available at server path"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )


# Export router
__all__ = ["router"]
