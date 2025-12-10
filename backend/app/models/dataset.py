"""
Dataset model - represents uploaded datasets for data analysis.

Datasets contain file information, processing status, and schema metadata.
"""

from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, BigInteger, Integer, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.record import Record
    from app.models.file import File
    from app.models.visualization import Visualization
    from app.models.insight import Insight


class DatasetStatus(str, PyEnum):
    """Status of dataset processing."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Dataset(BaseModel):
    """
    Dataset model - represents uploaded data files.

    Datasets belong to organizations and are created by users.
    They track file metadata, processing status, and schema information.
    """

    __tablename__ = "datasets"

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Dataset name (user-provided or derived from filename)"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of the dataset"
    )

    # File Information
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename of uploaded file"
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
        comment="SHA-256 hash for deduplication and integrity checking"
    )

    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="S3 key or file path where the dataset is stored"
    )

    # Processing Status
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status_enum"),
        default=DatasetStatus.UPLOADING,
        nullable=False,
        index=True,
        comment="Current processing status of the dataset"
    )

    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )

    # Data Schema Information
    row_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of rows in the dataset"
    )

    column_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of columns in the dataset"
    )

    schema_info: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Schema metadata including column names, types, and statistics"
    )

    # Creator/Owner
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created/uploaded this dataset"
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="datasets"
    )

    records: Mapped[list["Record"]] = relationship(
        "Record",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    source_file: Mapped[Optional["File"]] = relationship(
        "File",
        back_populates="dataset",
        foreign_keys="File.dataset_id",
        uselist=False
    )

    visualizations: Mapped[list["Visualization"]] = relationship(
        "Visualization",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    insights: Mapped[list["Insight"]] = relationship(
        "Insight",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Dataset(id={self.id}, name='{self.name}', status={self.status.value}, org_id={self.organization_id})>"

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def is_ready(self) -> bool:
        """Check if dataset is ready for use."""
        return self.status == DatasetStatus.READY

    @property
    def is_processing(self) -> bool:
        """Check if dataset is currently being processed."""
        return self.status in [DatasetStatus.UPLOADING, DatasetStatus.PROCESSING]

    @property
    def has_failed(self) -> bool:
        """Check if dataset processing has failed."""
        return self.status == DatasetStatus.FAILED
