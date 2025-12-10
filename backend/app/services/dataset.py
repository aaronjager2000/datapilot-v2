"""
Dataset service layer for business logic.

Handles dataset creation, retrieval, updates, deletion, and processing
with comprehensive error handling and validation.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dataset import Dataset, DatasetStatus
from app.models.record import Record
from app.models.file import File, StorageLocation
from app.models.user import User
from app.utils.file_handler import save_upload_file, get_file_hash, get_file_metadata
from app.utils.s3_client import S3Client
from app.workers.ingestion_worker import process_dataset
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatasetServiceError(Exception):
    """Base exception for dataset service errors."""
    pass


class DatasetNotFoundError(DatasetServiceError):
    """Raised when dataset is not found."""
    pass


async def create_dataset(
    db: AsyncSession,
    file: UploadFile,
    metadata: Dict[str, Any],
    user: User,
    organization_id: UUID
) -> Dataset:
    """
    Handle full dataset upload flow.
    
    Steps:
    1. Save file temporarily
    2. Calculate file hash
    3. Upload to S3 (or local storage)
    4. Create File record
    5. Create Dataset record
    6. Trigger background processing task
    
    Args:
        db: Database session
        file: Uploaded file
        metadata: Dataset metadata (name, description, etc.)
        user: User creating the dataset
        organization_id: Organization ID
    
    Returns:
        Created Dataset model
    
    Raises:
        DatasetServiceError: If creation fails
    """
    try:
        logger.info(f"Creating dataset from file: {file.filename}")
        
        # Step 1: Save file temporarily
        temp_path = await save_upload_file(file, str(organization_id), "temp")
        
        # Step 2: Get file metadata and hash
        file_meta = get_file_metadata(temp_path)
        file_hash = get_file_hash(temp_path)
        
        logger.info(f"File metadata: size={file_meta['size_mb']}MB, hash={file_hash[:16]}...")
        
        # Step 3: Upload to storage
        storage_path = await _upload_to_storage(temp_path, file.filename, organization_id)
        
        # Step 4: Create File record
        file_record = File(
            organization_id=organization_id,
            uploaded_by=user.id,
            file_name=file.filename,
            file_size=file_meta['size'],
            file_hash=file_hash,
            file_path=storage_path,
            mime_type=file_meta['mime_type'],
            storage_location=StorageLocation.S3 if settings.STORAGE_TYPE == "s3" else StorageLocation.LOCAL
        )
        
        db.add(file_record)
        await db.flush()
        
        # Step 5: Create Dataset record
        dataset_name = metadata.get('name', file.filename)
        description = metadata.get('description')
        
        dataset = Dataset(
            organization_id=organization_id,
            created_by=user.id,
            name=dataset_name,
            description=description,
            file_name=file.filename,
            file_size=file_meta['size'],
            file_hash=file_hash,
            file_path=storage_path,
            status=DatasetStatus.UPLOADING
        )
        
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)
        
        # Link file to dataset
        file_record.dataset_id = dataset.id
        await db.commit()
        
        logger.info(f"Created dataset {dataset.id} with status {dataset.status}")
        
        # Step 6: Trigger background processing
        process_dataset.delay(str(dataset.id))
        logger.info(f"Triggered background processing for dataset {dataset.id}")
        
        return dataset
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create dataset: {e}", exc_info=True)
        raise DatasetServiceError(f"Dataset creation failed: {str(e)}")


async def get_dataset(
    db: AsyncSession,
    dataset_id: UUID,
    organization_id: UUID
) -> Optional[Dataset]:
    """
    Retrieve dataset with full schema information.
    
    Args:
        db: Database session
        dataset_id: Dataset ID
        organization_id: Organization ID for tenant isolation
    
    Returns:
        Dataset model or None if not found
    """
    try:
        stmt = select(Dataset).where(
            and_(
                Dataset.id == dataset_id,
                Dataset.organization_id == organization_id,
                Dataset.deleted_at.is_(None)
            )
        ).options(selectinload(Dataset.creator))
        
        result = await db.execute(stmt)
        dataset = result.scalar_one_or_none()
        
        return dataset
    
    except Exception as e:
        logger.error(f"Failed to get dataset {dataset_id}: {e}")
        raise DatasetServiceError(f"Failed to retrieve dataset: {str(e)}")


async def list_datasets(
    db: AsyncSession,
    organization_id: UUID,
    filters: Optional[Dict[str, Any]] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Dataset], int]:
    """
    List datasets with filtering and pagination.
    
    Args:
        db: Database session
        organization_id: Organization ID
        filters: Optional filters:
            - status: Filter by dataset status
            - created_by: Filter by creator user ID
            - date_from: Filter by creation date (from)
            - date_to: Filter by creation date (to)
            - search: Search in name/description
        skip: Number of records to skip
        limit: Maximum records to return
    
    Returns:
        Tuple of (list of datasets, total count)
    """
    try:
        # Base query
        base_stmt = select(Dataset).where(
            and_(
                Dataset.organization_id == organization_id,
                Dataset.deleted_at.is_(None)
            )
        )
        
        # Apply filters
        if filters:
            # Status filter
            if 'status' in filters and filters['status']:
                base_stmt = base_stmt.where(Dataset.status == filters['status'])
            
            # Creator filter
            if 'created_by' in filters and filters['created_by']:
                base_stmt = base_stmt.where(Dataset.created_by == filters['created_by'])
            
            # Date range filters
            if 'date_from' in filters and filters['date_from']:
                base_stmt = base_stmt.where(Dataset.created_at >= filters['date_from'])
            
            if 'date_to' in filters and filters['date_to']:
                base_stmt = base_stmt.where(Dataset.created_at <= filters['date_to'])
            
            # Search filter
            if 'search' in filters and filters['search']:
                search_term = f"%{filters['search']}%"
                base_stmt = base_stmt.where(
                    or_(
                        Dataset.name.ilike(search_term),
                        Dataset.description.ilike(search_term)
                    )
                )
        
        # Get total count
        count_stmt = select(func.count()).select_from(base_stmt.alias())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()
        
        # Get paginated results
        stmt = base_stmt.options(
            selectinload(Dataset.creator)
        ).order_by(Dataset.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        datasets = result.scalars().all()
        
        logger.info(f"Listed {len(datasets)} datasets (total: {total})")
        return list(datasets), total
    
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        raise DatasetServiceError(f"Failed to list datasets: {str(e)}")


async def update_dataset(
    db: AsyncSession,
    dataset_id: UUID,
    organization_id: UUID,
    updates: Dict[str, Any]
) -> Dataset:
    """
    Update dataset metadata.
    
    Args:
        db: Database session
        dataset_id: Dataset ID
        organization_id: Organization ID
        updates: Dictionary of fields to update (name, description)
    
    Returns:
        Updated Dataset model
    
    Raises:
        DatasetNotFoundError: If dataset not found
        DatasetServiceError: If update fails
    """
    try:
        dataset = await get_dataset(db, dataset_id, organization_id)
        
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        
        # Update allowed fields
        if 'name' in updates:
            dataset.name = updates['name']
        
        if 'description' in updates:
            dataset.description = updates['description']
        
        dataset.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(dataset)
        
        logger.info(f"Updated dataset {dataset_id}")
        return dataset
    
    except DatasetNotFoundError:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update dataset {dataset_id}: {e}")
        raise DatasetServiceError(f"Failed to update dataset: {str(e)}")


async def delete_dataset(
    db: AsyncSession,
    dataset_id: UUID,
    organization_id: UUID
) -> bool:
    """
    Soft delete dataset and associated records.
    
    Args:
        db: Database session
        dataset_id: Dataset ID
        organization_id: Organization ID
    
    Returns:
        True if deleted successfully
    
    Raises:
        DatasetNotFoundError: If dataset not found
        DatasetServiceError: If deletion fails
    """
    try:
        dataset = await get_dataset(db, dataset_id, organization_id)
        
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        
        # Soft delete (set deleted_at timestamp)
        dataset.deleted_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"Soft deleted dataset {dataset_id}")
        return True
    
    except DatasetNotFoundError:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete dataset {dataset_id}: {e}")
        raise DatasetServiceError(f"Failed to delete dataset: {str(e)}")


async def get_dataset_preview(
    db: AsyncSession,
    dataset_id: UUID,
    organization_id: UUID,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get preview of dataset records.
    
    Args:
        db: Database session
        dataset_id: Dataset ID
        organization_id: Organization ID
        limit: Maximum number of records to return
    
    Returns:
        Dictionary with preview data:
        {
            'columns': [...],
            'records': [...],
            'total_count': int,
            'preview_count': int
        }
    
    Raises:
        DatasetNotFoundError: If dataset not found
    """
    try:
        dataset = await get_dataset(db, dataset_id, organization_id)
        
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        
        # Get total record count
        count_stmt = select(func.count()).select_from(Record).where(
            and_(
                Record.dataset_id == dataset_id,
                Record.organization_id == organization_id
            )
        )
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Get preview records
        stmt = select(Record).where(
            and_(
                Record.dataset_id == dataset_id,
                Record.organization_id == organization_id
            )
        ).order_by(Record.row_number).limit(limit)
        
        result = await db.execute(stmt)
        records = result.scalars().all()
        
        # Extract columns from schema_info or first record
        columns = []
        if dataset.schema_info and 'columns' in dataset.schema_info:
            columns = dataset.schema_info['columns']
        elif records:
            columns = list(records[0].data.keys())
        
        # Format records
        formatted_records = [
            {
                'row_number': record.row_number,
                'data': record.data,
                'is_valid': record.is_valid
            }
            for record in records
        ]
        
        preview_data = {
            'columns': columns,
            'records': formatted_records,
            'total_count': total_count,
            'preview_count': len(formatted_records)
        }
        
        logger.info(f"Retrieved preview for dataset {dataset_id}: {len(formatted_records)} of {total_count} records")
        return preview_data
    
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get dataset preview: {e}")
        raise DatasetServiceError(f"Failed to get preview: {str(e)}")


async def get_dataset_stats(
    db: AsyncSession,
    dataset_id: UUID,
    organization_id: UUID
) -> Dict[str, Any]:
    """
    Get statistics for all columns in the dataset.
    
    Args:
        db: Database session
        dataset_id: Dataset ID
        organization_id: Organization ID
    
    Returns:
        Dictionary with column statistics
    
    Raises:
        DatasetNotFoundError: If dataset not found
    """
    try:
        dataset = await get_dataset(db, dataset_id, organization_id)
        
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        
        # Get stats from schema_info if available
        if dataset.schema_info and 'column_stats' in dataset.schema_info:
            stats = dataset.schema_info['column_stats']
        else:
            stats = {}
        
        # Add dataset-level stats
        result = {
            'dataset_id': str(dataset_id),
            'total_rows': dataset.row_count,
            'total_columns': dataset.column_count,
            'column_stats': stats
        }
        
        logger.info(f"Retrieved stats for dataset {dataset_id}")
        return result
    
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get dataset stats: {e}")
        raise DatasetServiceError(f"Failed to get stats: {str(e)}")


async def reprocess_dataset(
    db: AsyncSession,
    dataset_id: UUID,
    organization_id: UUID,
    settings: Optional[Dict[str, Any]] = None
) -> Dataset:
    """
    Re-run ingestion pipeline for a dataset.
    
    Args:
        db: Database session
        dataset_id: Dataset ID
        organization_id: Organization ID
        settings: Optional processing settings
    
    Returns:
        Updated Dataset model
    
    Raises:
        DatasetNotFoundError: If dataset not found
        DatasetServiceError: If reprocessing fails
    """
    try:
        dataset = await get_dataset(db, dataset_id, organization_id)
        
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        
        # Delete existing records
        delete_stmt = Record.__table__.delete().where(
            and_(
                Record.dataset_id == dataset_id,
                Record.organization_id == organization_id
            )
        )
        await db.execute(delete_stmt)
        
        # Reset dataset status
        dataset.status = DatasetStatus.PROCESSING
        dataset.processing_error = None
        dataset.row_count = None
        dataset.column_count = None
        
        # Update settings if provided
        if settings:
            if not dataset.schema_info:
                dataset.schema_info = {}
            dataset.schema_info['reprocess_settings'] = settings
        
        await db.commit()
        await db.refresh(dataset)
        
        # Trigger background processing
        process_dataset.delay(str(dataset.id))
        logger.info(f"Triggered reprocessing for dataset {dataset_id}")
        
        return dataset
    
    except DatasetNotFoundError:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reprocess dataset {dataset_id}: {e}")
        raise DatasetServiceError(f"Failed to reprocess dataset: {str(e)}")


# Helper functions

async def _upload_to_storage(temp_path: str, filename: str, organization_id: UUID) -> str:
    """
    Upload file to configured storage backend.
    
    Args:
        temp_path: Temporary file path
        filename: Original filename
        organization_id: Organization ID
    
    Returns:
        Storage path (S3 key or local path)
    """
    try:
        if settings.STORAGE_TYPE in ["s3", "r2"]:
            # Upload to S3/R2
            s3_client = S3Client()
            storage_path = f"datasets/{organization_id}/{filename}"
            s3_client.upload_file(temp_path, storage_path)
            logger.info(f"Uploaded to S3: {storage_path}")
            return storage_path
        else:
            # Use local storage (move file)
            import shutil
            from pathlib import Path
            import os
            
            # Resolve to absolute path
            base_dir = Path(settings.LOCAL_UPLOAD_DIR)
            if not base_dir.is_absolute():
                # If relative, resolve from backend directory
                backend_dir = Path(__file__).parent.parent.parent  # Go to backend/
                base_dir = backend_dir / base_dir
            
            storage_dir = base_dir / str(organization_id) / "datasets"
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            storage_path = storage_dir / filename
            abs_storage_path = storage_path.absolute()
            
            logger.info(f"Saving file to: {abs_storage_path}")
            
            # Read the temp file content and write directly to final location
            # This avoids any file handle issues with shutil.copy
            try:
                with open(temp_path, 'rb') as src:
                    file_content = src.read()
                    
                # Write to final location with explicit flush and sync
                with open(abs_storage_path, 'wb') as dst:
                    dst.write(file_content)
                    dst.flush()
                    os.fsync(dst.fileno())  # Force write to disk
                
                logger.info(f"✓ File written: {len(file_content)} bytes")
                
                # Verify immediately
                if not os.path.exists(abs_storage_path):
                    raise IOError(f"File write completed but file not found at {abs_storage_path}")
                
                verify_size = os.path.getsize(abs_storage_path)
                if verify_size != len(file_content):
                    raise IOError(f"File size mismatch: wrote {len(file_content)} but found {verify_size}")
                
                logger.info(f"✓ Verified: {verify_size} bytes at {abs_storage_path}")
                
            finally:
                # Clean up temp file
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")
            
            return str(abs_storage_path)
    
    except Exception as e:
        logger.error(f"Failed to upload to storage: {e}")
        raise


# Export main functions
__all__ = [
    "create_dataset",
    "get_dataset",
    "list_datasets",
    "update_dataset",
    "delete_dataset",
    "get_dataset_preview",
    "get_dataset_stats",
    "reprocess_dataset",
    "DatasetServiceError",
    "DatasetNotFoundError"
]
