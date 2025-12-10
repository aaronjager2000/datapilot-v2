

import logging
from typing import Optional, BinaryIO
from pathlib import Path
import mimetypes

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Client:
    
    def __init__(self):
        """Initialize S3 client with credentials from settings."""
        self._client = None
        self._bucket_name = settings.S3_BUCKET_NAME

        if settings.STORAGE_TYPE not in ["s3", "r2"]:
            logger.warning(f"Storage type '{settings.STORAGE_TYPE}' is not S3/R2. S3Client will not be initialized.")
            return

        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            logger.error("S3/R2 credentials not configured. S3Client cannot be initialized.")
            return

        # Configure boto3 client
        config = Config(
            region_name=settings.AWS_REGION,
            signature_version='s3v4',
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )

        client_kwargs = {
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
            'config': config,
        }

        # Add endpoint URL for R2 or custom S3 endpoints
        if settings.S3_ENDPOINT_URL:
            client_kwargs['endpoint_url'] = settings.S3_ENDPOINT_URL
            logger.info(f"Using custom S3 endpoint: {settings.S3_ENDPOINT_URL}")

        self._client = boto3.client('s3', **client_kwargs)
        logger.info(f"S3 client initialized for bucket: {self._bucket_name}")

    @property
    def client(self):
        """Get boto3 S3 client."""
        if not self._client:
            raise RuntimeError("S3 client not initialized. Check storage configuration.")
        return self._client

    def _get_content_type(self, filename: str) -> str:
        """Detect content type from filename."""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'

    def build_key(
        self,
        organization_id: str,
        dataset_id: str,
        filename: str
    ) -> str:
        """
        Build S3 key with organization/dataset structure.

        Format: {organization_id}/datasets/{dataset_id}/{filename}
        """
        return f"{organization_id}/datasets/{dataset_id}/{filename}"

    async def upload_file(
        self,
        file_path: str,
        key: str,
        bucket: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> bool:
        """
        Upload a file from filesystem to S3/R2.

        Args:
            file_path: Path to local file
            key: S3 object key (path in bucket)
            bucket: Bucket name (uses default if not specified)
            content_type: MIME type (auto-detected if not specified)

        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self._bucket_name

        if not content_type:
            content_type = self._get_content_type(file_path)

        try:
            self.client.upload_file(
                file_path,
                bucket,
                key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            logger.info(f"Successfully uploaded file to s3://{bucket}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return False

    async def upload_fileobj(
        self,
        file_obj: BinaryIO,
        key: str,
        bucket: Optional[str] = None,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> bool:
        """
        Upload a file-like object to S3/R2.

        Useful for FastAPI UploadFile objects.

        Args:
            file_obj: File-like object to upload
            key: S3 object key (path in bucket)
            bucket: Bucket name (uses default if not specified)
            content_type: MIME type (auto-detected from filename if not specified)
            filename: Original filename (for content-type detection)

        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self._bucket_name

        if not content_type and filename:
            content_type = self._get_content_type(filename)
        elif not content_type:
            content_type = 'application/octet-stream'

        try:
            self.client.upload_fileobj(
                file_obj,
                bucket,
                key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            logger.info(f"Successfully uploaded file object to s3://{bucket}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload file object to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading file object: {e}")
            return False

    async def download_file(
        self,
        key: str,
        dest_path: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """
        Download a file from S3/R2 to local filesystem.

        Args:
            key: S3 object key (path in bucket)
            dest_path: Local destination path
            bucket: Bucket name (uses default if not specified)

        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self._bucket_name

        # Ensure destination directory exists
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            self.client.download_file(bucket, key, dest_path)
            logger.info(f"Successfully downloaded s3://{bucket}/{key} to {dest_path}")
            return True

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {e}")
            return False

    async def generate_presigned_url(
        self,
        key: str,
        bucket: Optional[str] = None,
        expiration: int = 3600,
        method: str = 'get_object',
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary file access.

        Args:
            key: S3 object key (path in bucket)
            bucket: Bucket name (uses default if not specified)
            expiration: URL expiration time in seconds (default 1 hour)
            method: S3 method ('get_object' for download, 'put_object' for upload)

        Returns:
            Presigned URL string, or None if failed
        """
        bucket = bucket or self._bucket_name

        try:
            url = self.client.generate_presigned_url(
                method,
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for s3://{bucket}/{key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None

    async def delete_file(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """
        Delete a file from S3/R2.

        Args:
            key: S3 object key (path in bucket)
            bucket: Bucket name (uses default if not specified)

        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self._bucket_name

        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Successfully deleted s3://{bucket}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file: {e}")
            return False

    async def list_files(
        self,
        prefix: str,
        bucket: Optional[str] = None,
        max_keys: int = 1000,
    ) -> list[dict]:
        """
        List files in S3/R2 with a given prefix.

        Useful for listing all files in an organization/dataset.

        Args:
            prefix: Key prefix to filter by (e.g., "org-id/datasets/dataset-id/")
            bucket: Bucket name (uses default if not specified)
            max_keys: Maximum number of keys to return

        Returns:
            List of file metadata dicts with keys: 'Key', 'Size', 'LastModified'
        """
        bucket = bucket or self._bucket_name

        try:
            response = self.client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            files = [
                {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                }
                for obj in response['Contents']
            ]

            logger.info(f"Listed {len(files)} files with prefix: {prefix}")
            return files

        except ClientError as e:
            logger.error(f"Failed to list files from S3: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files: {e}")
            return []

    async def file_exists(
        self,
        key: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """
        Check if a file exists in S3/R2.

        Args:
            key: S3 object key (path in bucket)
            bucket: Bucket name (uses default if not specified)

        Returns:
            True if file exists, False otherwise
        """
        bucket = bucket or self._bucket_name

        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking if file exists: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking file existence: {e}")
            return False


# Singleton instance
_s3_client: Optional[S3Client] = None


def get_s3_client() -> S3Client:
    """
    Get or create S3Client singleton instance.

    Returns:
        S3Client instance
    """
    global _s3_client

    if _s3_client is None:
        _s3_client = S3Client()

    return _s3_client
