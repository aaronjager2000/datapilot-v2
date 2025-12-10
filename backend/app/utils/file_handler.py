"""
File handling utilities for upload management and file operations.
"""

import hashlib
import logging
import mimetypes
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)


async def save_upload_file(
    upload_file: UploadFile,
    organization_id: str,
    subfolder: str = "temp"
) -> str:
    """
    Save an uploaded file temporarily to local filesystem.

    Args:
        upload_file: FastAPI UploadFile object
        organization_id: Organization ID for file organization
        subfolder: Subfolder within upload directory (default: "temp")

    Returns:
        str: Absolute path to the saved file

    Raises:
        IOError: If file cannot be saved
    """
    # Create directory structure: uploads/{organization_id}/{subfolder}
    upload_dir = Path(settings.LOCAL_UPLOAD_DIR) / organization_id / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename to avoid collisions
    # Format: {timestamp}_{uuid}_{original_filename}
    timestamp = int(time.time())
    unique_id = str(uuid4())[:8]
    safe_filename = upload_file.filename.replace("/", "_").replace("\\", "_")
    filename = f"{timestamp}_{unique_id}_{safe_filename}"

    file_path = upload_dir / filename

    try:
        # Write file in chunks to handle large files efficiently
        with open(file_path, "wb") as buffer:
            # Read and write in 1MB chunks
            chunk_size = 1024 * 1024
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                buffer.write(chunk)

        logger.info(f"Saved upload file to: {file_path}")
        return str(file_path)

    except Exception as e:
        # Clean up partial file if write failed
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Failed to save upload file: {e}")
        raise IOError(f"Failed to save file: {str(e)}")


def get_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """
    Generate hash of a file for deduplication and integrity checking.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (default: "sha256")

    Returns:
        str: Hexadecimal hash string

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If algorithm is not supported
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Validate algorithm
    try:
        hasher = hashlib.new(algorithm)
    except ValueError:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    try:
        # Read file in chunks to handle large files
        with open(path, "rb") as f:
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)

        file_hash = hasher.hexdigest()
        logger.debug(f"Generated {algorithm} hash for {file_path}: {file_hash}")
        return file_hash

    except Exception as e:
        logger.error(f"Failed to generate hash for {file_path}: {e}")
        raise


def get_file_metadata(file_path: str) -> dict:
    """
    Get metadata about a file.

    Args:
        file_path: Path to the file

    Returns:
        dict: File metadata including:
            - size: File size in bytes
            - size_mb: File size in MB (rounded to 2 decimals)
            - mime_type: MIME type
            - extension: File extension (without dot)
            - filename: Original filename
            - created_at: Creation timestamp
            - modified_at: Last modification timestamp

    Raises:
        FileNotFoundError: If file does not exist
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        stat = path.stat()

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "application/octet-stream"

        # Get extension (without dot)
        extension = path.suffix.lstrip(".").lower() if path.suffix else ""

        metadata = {
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "mime_type": mime_type,
            "extension": extension,
            "filename": path.name,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

        logger.debug(f"Retrieved metadata for {file_path}: {metadata}")
        return metadata

    except Exception as e:
        logger.error(f"Failed to get metadata for {file_path}: {e}")
        raise


def validate_file_type(
    file_path: str,
    allowed_types: Optional[List[str]] = None,
    allowed_extensions: Optional[List[str]] = None
) -> bool:
    """
    Validate file type against allowed types/extensions.

    Args:
        file_path: Path to the file
        allowed_types: List of allowed MIME types (e.g., ["text/csv", "application/json"])
        allowed_extensions: List of allowed extensions (e.g., ["csv", "xlsx", "json"])

    Returns:
        bool: True if file type is valid, False otherwise

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If neither allowed_types nor allowed_extensions is provided
    """
    if not allowed_types and not allowed_extensions:
        raise ValueError("Must provide either allowed_types or allowed_extensions")

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        # Get file metadata
        metadata = get_file_metadata(file_path)
        mime_type = metadata["mime_type"]
        extension = metadata["extension"]

        # Check MIME type
        if allowed_types:
            # Support wildcards like "image/*"
            for allowed_type in allowed_types:
                if allowed_type.endswith("/*"):
                    # Wildcard match (e.g., "image/*" matches "image/png")
                    prefix = allowed_type[:-2]
                    if mime_type.startswith(prefix + "/"):
                        logger.debug(f"File {file_path} matches MIME wildcard: {allowed_type}")
                        return True
                elif mime_type == allowed_type:
                    logger.debug(f"File {file_path} matches MIME type: {allowed_type}")
                    return True

        # Check extension
        if allowed_extensions:
            # Normalize extensions (remove dots, lowercase)
            normalized_allowed = [ext.lstrip(".").lower() for ext in allowed_extensions]
            if extension in normalized_allowed:
                logger.debug(f"File {file_path} matches extension: {extension}")
                return True

        logger.warning(
            f"File {file_path} validation failed. "
            f"MIME: {mime_type}, Extension: {extension}, "
            f"Allowed MIME: {allowed_types}, Allowed Extensions: {allowed_extensions}"
        )
        return False

    except Exception as e:
        logger.error(f"Failed to validate file type for {file_path}: {e}")
        raise


def cleanup_temp_files(
    older_than: Optional[timedelta] = None,
    organization_id: Optional[str] = None,
    subfolder: str = "temp"
) -> int:
    """
    Delete old temporary files to free up storage.

    Args:
        older_than: Delete files older than this timedelta (default: 24 hours)
        organization_id: Limit cleanup to specific organization (None = all orgs)
        subfolder: Subfolder to clean (default: "temp")

    Returns:
        int: Number of files deleted

    Raises:
        IOError: If cleanup operation fails
    """
    if older_than is None:
        older_than = timedelta(hours=24)

    cutoff_time = time.time() - older_than.total_seconds()
    deleted_count = 0

    # Determine base directory
    base_dir = Path(settings.LOCAL_UPLOAD_DIR)
    if not base_dir.exists():
        logger.info(f"Upload directory does not exist: {base_dir}")
        return 0

    try:
        # Build search path
        if organization_id:
            search_dirs = [base_dir / organization_id / subfolder]
        else:
            # Search all organization directories
            search_dirs = []
            for org_dir in base_dir.iterdir():
                if org_dir.is_dir():
                    temp_dir = org_dir / subfolder
                    if temp_dir.exists():
                        search_dirs.append(temp_dir)

        # Clean up old files
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for file_path in search_dir.iterdir():
                if not file_path.is_file():
                    continue

                # Check if file is old enough
                try:
                    file_mtime = file_path.stat().st_mtime
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

        logger.info(
            f"Cleanup complete. Deleted {deleted_count} files older than {older_than}"
        )
        return deleted_count

    except Exception as e:
        logger.error(f"Failed to cleanup temp files: {e}")
        raise IOError(f"Cleanup operation failed: {str(e)}")


def get_safe_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other issues.

    Args:
        filename: Original filename

    Returns:
        str: Safe filename with dangerous characters removed
    """
    # Remove path separators and other dangerous characters
    safe = filename.replace("/", "_").replace("\\", "_").replace("..", "_")

    # Remove null bytes
    safe = safe.replace("\0", "")

    # Limit length
    if len(safe) > 255:
        # Preserve extension
        name, ext = os.path.splitext(safe)
        max_name_len = 255 - len(ext)
        safe = name[:max_name_len] + ext

    return safe


def ensure_upload_directory() -> Path:
    """
    Ensure the upload directory exists and is writable.

    Returns:
        Path: Path to upload directory

    Raises:
        IOError: If directory cannot be created or is not writable
    """
    upload_dir = Path(settings.LOCAL_UPLOAD_DIR)

    try:
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Test write permission
        test_file = upload_dir / ".write_test"
        test_file.touch()
        test_file.unlink()

        logger.debug(f"Upload directory ready: {upload_dir}")
        return upload_dir

    except Exception as e:
        logger.error(f"Failed to ensure upload directory: {e}")
        raise IOError(f"Upload directory not accessible: {str(e)}")
