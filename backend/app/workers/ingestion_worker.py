"""
Celery worker for data ingestion tasks.

Handles end-to-end dataset processing including file parsing, type inference,
validation, cleaning, normalization, and bulk record insertion.
"""

import logging
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.workers.tasks import BaseTask
from app.db.session import SyncSessionLocal
from app.models.dataset import Dataset, DatasetStatus
from app.models.record import Record
from app.utils.s3_client import S3Client
from app.core.redis import get_redis_client_sync
from app.services.data_ingestion.parser import parse_csv, parse_excel, FileParserError
from app.services.data_ingestion.type_inference import infer_column_types, get_column_stats, TypeInferenceError
from app.services.data_ingestion.validator import get_validation_summary, ValidationError
from app.services.transformation.cleaner import (
    remove_duplicates,
    handle_missing_values,
    trim_whitespace,
    CleaningError
)
from app.services.transformation.normalizer import (
    normalize_column_names,
    NormalizationError
)

logger = logging.getLogger(__name__)

# Batch size for bulk inserting records
BATCH_SIZE = 1000


def send_dataset_websocket_update(
    dataset_id: str,
    status: str,
    progress: int,
    message: str,
    organization_id: Optional[str] = None
):
    """
    Send dataset update via WebSocket.
    
    Publishes to both dataset-specific and organization channels.
    
    Args:
        dataset_id: Dataset ID
        status: Processing status
        progress: Progress percentage (0-100)
        message: Status message
        organization_id: Optional organization ID for broadcasting
    """
    try:
        import json
        redis = get_redis_client_sync()
        
        update_data = {
            "type": "dataset_update",
            "dataset_id": dataset_id,
            "status": status,
            "progress": progress,
            "message": message
        }
        
        # Publish to dataset channel
        redis.publish(f"ws:dataset:{dataset_id}", json.dumps(update_data))
        
        # Also publish to organization channel if provided
        if organization_id:
            redis.publish(f"ws:organization:{organization_id}", json.dumps(update_data))
        
        logger.debug(f"Sent WebSocket update for dataset {dataset_id}: {progress}%")
    
    except Exception as e:
        # Don't fail the task if WebSocket update fails
        logger.warning(f"Failed to send WebSocket update: {e}")


@celery_app.task(
    base=BaseTask,
    name="app.workers.ingestion_worker.process_dataset",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def process_dataset(self, dataset_id: str) -> Dict[str, Any]:
    """
    Process a dataset end-to-end.
    
    Steps:
    1. Retrieve dataset from database
    2. Download file from S3 to temp location
    3. Parse file (CSV/Excel) using parser service
    4. Infer column types using type inference service
    5. Update dataset schema_info with column metadata
    6. Validate data using validation rules (if any)
    7. Clean data using cleaner service
    8. Normalize data using normalizer service
    9. Bulk insert records into Record table (use batching for large datasets)
    10. Update dataset status to "ready" and set row_count, column_count
    11. Delete temp file
    12. If error occurs, update dataset status to "failed" and store error message
    13. Emit progress updates throughout (0%, 25%, 50%, 75%, 100%)
    
    Args:
        dataset_id: UUID of the dataset to process
    
    Returns:
        Dictionary with processing results
    """
    db: Optional[Session] = None
    temp_file_path: Optional[str] = None
    dataset: Optional[Dataset] = None
    
    try:
        # Initialize database session
        db = SyncSessionLocal()
        
        # Step 1: Retrieve dataset from database (0% progress)
        self.update_progress(0, 100, "processing", "Retrieving dataset from database")
        logger.info(f"Starting processing for dataset {dataset_id}")
        
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Update status to processing
        dataset.status = DatasetStatus.PROCESSING
        dataset.processing_error = None
        db.commit()
        
        # Send WebSocket update
        send_dataset_websocket_update(
            dataset_id=dataset_id,
            status="processing",
            progress=0,
            message="Starting dataset processing",
            organization_id=str(dataset.organization_id)
        )
        
        # Step 2: Download file from S3 to temp location (5% progress)
        self.update_progress(5, 100, "processing", "Downloading file from storage")
        logger.info(f"Downloading file: {dataset.file_path}")
        
        temp_file_path = _download_file_to_temp(dataset.file_path)
        
        # Step 3: Parse file (10% progress)
        self.update_progress(10, 100, "processing", f"Parsing {dataset.file_name}")
        send_dataset_websocket_update(dataset_id, "processing", 10, "Parsing file", str(dataset.organization_id))
        logger.info(f"Parsing file: {temp_file_path}")
        
        df = _parse_file(temp_file_path, dataset.file_name)
        
        if df is None or df.empty:
            raise ValueError("Parsed DataFrame is empty")
        
        logger.info(f"Parsed {len(df)} rows and {len(df.columns)} columns")
        
        # Step 4: Infer column types (25% progress)
        self.update_progress(25, 100, "processing", "Inferring column types")
        send_dataset_websocket_update(dataset_id, "processing", 25, "Inferring column types", str(dataset.organization_id))
        logger.info("Inferring column types")
        
        type_info = infer_column_types(df)
        
        # Get column statistics
        column_stats = {}
        for column in df.columns:
            try:
                stats = get_column_stats(df, column)
                column_stats[column] = stats
            except Exception as e:
                logger.warning(f"Failed to get stats for column {column}: {e}")
                column_stats[column] = {"error": str(e)}
        
        # Step 5: Update dataset schema_info (30% progress)
        self.update_progress(30, 100, "processing", "Updating schema metadata")
        
        schema_info = {
            "columns": list(df.columns),
            "type_info": type_info,
            "column_stats": column_stats,
            "original_row_count": len(df),
            "original_column_count": len(df.columns)
        }
        
        dataset.schema_info = schema_info
        db.commit()
        logger.info("Schema info updated")
        
        # Step 6: Validate data (40% progress)
        self.update_progress(40, 100, "processing", "Validating data")
        logger.info("Validating data")
        
        validation_results = _validate_data(df, dataset)
        schema_info["validation_results"] = validation_results
        dataset.schema_info = schema_info
        db.commit()
        
        # Step 7: Clean data (50% progress)
        self.update_progress(50, 100, "processing", "Cleaning data")
        logger.info("Cleaning data")
        
        df_cleaned, cleaning_reports = _clean_data(df)
        schema_info["cleaning_reports"] = [report.to_dict() for report in cleaning_reports]
        dataset.schema_info = schema_info
        db.commit()
        
        logger.info(f"Data cleaned: {len(df_cleaned)} rows remaining")
        
        # Step 8: Normalize data (60% progress)
        self.update_progress(60, 100, "processing", "Normalizing data")
        logger.info("Normalizing data")
        
        df_normalized = _normalize_data(df_cleaned)
        
        # Update schema info with normalized column names
        schema_info["normalized_columns"] = list(df_normalized.columns)
        dataset.schema_info = schema_info
        db.commit()
        
        # Step 9: Bulk insert records (60-90% progress)
        self.update_progress(60, 100, "processing", "Inserting records into database")
        logger.info(f"Bulk inserting {len(df_normalized)} records")
        
        records_inserted = _bulk_insert_records(
            db,
            df_normalized,
            dataset,
            progress_callback=lambda current, total: self.update_progress(
                60 + int((current / total) * 30),  # 60% to 90%
                100,
                "processing",
                f"Inserting records: {current}/{total}"
            )
        )
        
        logger.info(f"Inserted {records_inserted} records")
        
        # Step 10: Update dataset status to "ready" (95% progress)
        self.update_progress(95, 100, "processing", "Finalizing dataset")
        
        dataset.status = DatasetStatus.READY
        dataset.row_count = len(df_normalized)
        dataset.column_count = len(df_normalized.columns)
        dataset.processing_error = None
        
        # Add final metadata
        schema_info["final_row_count"] = len(df_normalized)
        schema_info["final_column_count"] = len(df_normalized.columns)
        schema_info["records_inserted"] = records_inserted
        dataset.schema_info = schema_info
        
        db.commit()
        
        # Step 11: Delete temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"Deleted temp file: {temp_file_path}")
        
        # Step 13: Complete (100% progress)
        self.update_progress(100, 100, "completed", "Dataset processing completed")
        send_dataset_websocket_update(
            dataset_id,
            "ready",
            100,
            "Dataset ready for use",
            str(dataset.organization_id)
        )
        
        result = {
            "dataset_id": str(dataset.id),
            "status": "success",
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "records_inserted": records_inserted,
            "validation_passed": validation_results.get("passed", True),
            "cleaning_operations": len(cleaning_reports)
        }
        
        logger.info(f"Dataset {dataset_id} processed successfully: {result}")
        return result
    
    except Exception as e:
        # Step 12: Handle errors
        error_message = str(e)
        logger.error(f"Failed to process dataset {dataset_id}: {error_message}", exc_info=True)
        
        # Update dataset status to failed
        if db and dataset:
            try:
                dataset.status = DatasetStatus.FAILED
                dataset.processing_error = error_message
                db.commit()
                
                # Send WebSocket update about failure
                send_dataset_websocket_update(
                    dataset_id,
                    "failed",
                    0,
                    f"Processing failed: {error_message}",
                    str(dataset.organization_id)
                )
            except Exception as db_error:
                logger.error(f"Failed to update dataset status: {db_error}")
        
        # Update progress
        self.update_progress(
            0, 100, "failed",
            f"Processing failed: {error_message}"
        )
        
        # Clean up temp file if it exists
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to delete temp file: {cleanup_error}")
        
        # Re-raise for Celery retry mechanism
        raise
    
    finally:
        # Ensure database session is closed
        if db:
            db.close()


def _download_file_to_temp(file_path: str) -> str:
    """
    Download file from S3 to temporary location or use local file.
    
    Args:
        file_path: S3 key or local file path
    
    Returns:
        Path to file (temp or local)
    """
    try:
        from app.core.config import settings
        
        # If using local storage, handle both absolute and relative paths
        if settings.STORAGE_TYPE == "local":
            from pathlib import Path
            
            logger.info(f"Checking local file: {file_path}")
            logger.info(f"File is absolute: {os.path.isabs(file_path)}")
            
            # If relative, resolve from backend directory
            if not os.path.isabs(file_path):
                backend_dir = Path(__file__).parent.parent.parent  # Go up to backend/
                full_path = backend_dir / file_path
                file_path = str(full_path.resolve())
                logger.info(f"Resolved to absolute: {file_path}")
            
            # Check if file exists locally
            logger.info(f"Checking if exists: {os.path.exists(file_path)}")
            if os.path.exists(file_path):
                logger.info(f"✓ Using local file: {file_path}")
                return file_path
            else:
                # List what files ARE in the directory
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir):
                    files_in_dir = os.listdir(parent_dir)
                    logger.error(f"Directory exists but file not found. Files in {parent_dir}: {files_in_dir}")
                else:
                    logger.error(f"Parent directory doesn't exist: {parent_dir}")
                raise FileNotFoundError(f"Local file not found: {file_path}")
        
        # For S3/R2 storage, download to temp
        temp_dir = tempfile.mkdtemp(prefix="datapilot_")
        filename = os.path.basename(file_path)
        temp_file_path = os.path.join(temp_dir, filename)
        
        s3_client = S3Client()
        s3_client.download_file(file_path, temp_file_path)
        
        logger.info(f"Downloaded {file_path} to {temp_file_path}")
        return temp_file_path
    
    except Exception as e:
        logger.error(f"Failed to get file {file_path}: {e}")
        raise


def _parse_file(file_path: str, filename: str) -> pd.DataFrame:
    """
    Parse CSV or Excel file.
    
    Args:
        file_path: Path to file
        filename: Original filename
    
    Returns:
        Parsed DataFrame
    """
    try:
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == ".csv":
            df = parse_csv(file_path)
        elif file_ext in [".xlsx", ".xls"]:
            df = parse_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        return df
    
    except FileParserError as e:
        logger.error(f"Failed to parse file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing file: {e}")
        raise


def _validate_data(df: pd.DataFrame, dataset: Dataset) -> Dict[str, Any]:
    """
    Validate data using validation rules if any.
    
    Args:
        df: DataFrame to validate
        dataset: Dataset model with validation rules
    
    Returns:
        Validation results dictionary
    """
    try:
        # Check if dataset has validation rules
        validation_rules = {}
        if dataset.schema_info and "validation_rules" in dataset.schema_info:
            validation_rules = dataset.schema_info["validation_rules"]
        
        if not validation_rules:
            logger.info("No validation rules defined, skipping validation")
            return {
                "passed": True,
                "message": "No validation rules defined"
            }
        
        # Run validation
        summary = get_validation_summary(df, validation_rules)
        
        logger.info(
            f"Validation complete: {summary['total_errors']} errors, "
            f"{summary['total_warnings']} warnings"
        )
        
        return summary
    
    except ValidationError as e:
        logger.warning(f"Validation failed: {e}")
        return {
            "passed": False,
            "error": str(e)
        }
    except Exception as e:
        logger.warning(f"Unexpected error during validation: {e}")
        return {
            "passed": True,
            "warning": str(e)
        }


def _clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """
    Clean data using cleaner service.
    
    Args:
        df: DataFrame to clean
    
    Returns:
        Tuple of (cleaned_df, list_of_reports)
    """
    try:
        reports = []
        df_cleaned = df.copy()
        
        # Remove duplicates
        df_cleaned, report = remove_duplicates(df_cleaned)
        reports.append(report)
        
        # Trim whitespace from string columns
        df_cleaned, report = trim_whitespace(df_cleaned)
        reports.append(report)
        
        # Handle missing values (drop rows with all missing)
        df_cleaned, report = handle_missing_values(
            df_cleaned,
            strategy="drop_all"
        )
        reports.append(report)
        
        return df_cleaned, reports
    
    except CleaningError as e:
        logger.error(f"Cleaning failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during cleaning: {e}")
        raise


def _normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize data using normalizer service.
    
    Args:
        df: DataFrame to normalize
    
    Returns:
        Normalized DataFrame
    """
    try:
        # Normalize column names to snake_case
        df_normalized = normalize_column_names(df, case="snake")
        
        return df_normalized
    
    except NormalizationError as e:
        logger.error(f"Normalization failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during normalization: {e}")
        raise


def _bulk_insert_records(
    db: Session,
    df: pd.DataFrame,
    dataset: Dataset,
    progress_callback=None
) -> int:
    """
    Bulk insert records into database with batching.
    
    Args:
        db: Database session
        df: DataFrame with data to insert
        dataset: Dataset model
        progress_callback: Optional callback for progress updates
    
    Returns:
        Number of records inserted
    """
    try:
        records = []
        total_rows = len(df)
        inserted_count = 0
        
        # Convert DataFrame to records
        for idx, row in df.iterrows():
            # Convert row to dictionary, handling NaN values
            row_data = {}
            for col in df.columns:
                value = row[col]
                # Convert NaN to None for JSON serialization
                if pd.isna(value):
                    row_data[col] = None
                # Convert numpy types to Python types
                elif hasattr(value, 'item'):
                    row_data[col] = value.item()
                else:
                    row_data[col] = value
            
            record = Record(
                dataset_id=dataset.id,
                organization_id=dataset.organization_id,
                row_number=idx + 1,  # 1-indexed
                data=row_data,
                is_valid=True,
                validation_errors=None
            )
            
            records.append(record)
            
            # Batch insert when reaching batch size
            if len(records) >= BATCH_SIZE:
                db.bulk_save_objects(records)
                db.commit()
                inserted_count += len(records)
                
                logger.debug(f"Inserted batch of {len(records)} records ({inserted_count}/{total_rows})")
                
                # Update progress
                if progress_callback:
                    progress_callback(inserted_count, total_rows)
                
                records = []
        
        # Insert remaining records
        if records:
            db.bulk_save_objects(records)
            db.commit()
            inserted_count += len(records)
            logger.debug(f"Inserted final batch of {len(records)} records")
            
            # Final progress update
            if progress_callback:
                progress_callback(inserted_count, total_rows)
        
        return inserted_count
    
    except Exception as e:
        logger.error(f"Failed to bulk insert records: {e}")
        db.rollback()
        raise


@celery_app.task(
    base=BaseTask,
    name="app.workers.ingestion_worker.validate_file_task",
    bind=True
)
def validate_file_task(self, file_path: str) -> Dict[str, Any]:
    """
    Validate a file before processing (quick check).
    
    Args:
        file_path: Path to file to validate
    
    Returns:
        Validation results
    """
    try:
        self.update_progress(0, 100, "processing", "Validating file")
        
        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("File is empty")
        
        self.update_progress(50, 100, "processing", "Checking file format")
        
        # Try to parse first few rows
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == ".csv":
            df_sample = parse_csv(file_path, nrows=5)
        elif file_ext in [".xlsx", ".xls"]:
            df_sample = parse_excel(file_path)
            df_sample = df_sample.head(5)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        self.update_progress(100, 100, "completed", "Validation complete")
        
        return {
            "valid": True,
            "file_size": file_size,
            "sample_rows": len(df_sample),
            "sample_columns": len(df_sample.columns),
            "columns": list(df_sample.columns)
        }
    
    except Exception as e:
        logger.error(f"File validation failed: {e}")
        self.update_progress(0, 100, "failed", f"Validation failed: {str(e)}")
        
        return {
            "valid": False,
            "error": str(e)
        }


# Export tasks
__all__ = [
    "process_dataset",
    "validate_file_task"
]
