"""
File model - tracks all uploaded files before and after dataset processing.

Files exist independently of datasets, allowing for separation between
file upload and dataset processing stages.
"""

from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, BigInteger, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.dataset import Dataset


class StorageLocation(str, PyEnum):
    """Storage location for uploaded files."""
    LOCAL = "local"
    S3 = "s3"
    R2 = "r2"


class File(BaseModel):
    """
    File model - represents uploaded files.

    Tracks all file uploads separately from datasets, allowing files
    to exist before processing and providing better audit trail.
    """

    __tablename__ = "files"

    # Uploader Information
    uploaded_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who uploaded this file"
    )

    # File Metadata
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename"
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes"
    )

    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 hash for deduplication and integrity"
    )

    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Storage path or S3 key"
    )

    mime_type: Mapped[str] = mapped_column(
        String(127),
        nullable=False,
        comment="MIME type of the file"
    )

    storage_location: Mapped[StorageLocation] = mapped_column(
        Enum(StorageLocation, name="storage_location_enum"),
        nullable=False,
        index=True,
        comment="Where the file is stored"
    )

    # Link to Dataset (nullable - set after processing)
    dataset_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Dataset created from this file (set after processing)"
    )

    # Relationships
    uploader: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[uploaded_by],
        back_populates="uploaded_files"
    )

    dataset: Mapped[Optional["Dataset"]] = relationship(
        "Dataset",
        foreign_keys=[dataset_id],
        back_populates="source_file"
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, name='{self.file_name}', storage={self.storage_location.value}, org_id={self.organization_id})>"

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def file_size_kb(self) -> float:
        """Get file size in kilobytes."""
        return round(self.file_size / 1024, 2)

    @property
    def is_processed(self) -> bool:
        """Check if file has been processed into a dataset."""
        return self.dataset_id is not None

    @property
    def extension(self) -> str:
        """Get file extension from filename."""
        if "." in self.file_name:
            return self.file_name.rsplit(".", 1)[1].lower()
        return ""

    @property
    def is_csv(self) -> bool:
        """Check if file is a CSV."""
        return self.extension in ["csv", "txt"] or self.mime_type == "text/csv"

    @property
    def is_excel(self) -> bool:
        """Check if file is an Excel file."""
        excel_extensions = ["xls", "xlsx", "xlsm", "xlsb"]
        excel_mimes = [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ]
        return self.extension in excel_extensions or self.mime_type in excel_mimes

    @property
    def is_json(self) -> bool:
        """Check if file is JSON."""
        return self.extension == "json" or self.mime_type == "application/json"

    @property
    def file_type_category(self) -> str:
        """Get general file type category."""
        if self.is_csv:
            return "csv"
        elif self.is_excel:
            return "excel"
        elif self.is_json:
            return "json"
        else:
            return "other"
