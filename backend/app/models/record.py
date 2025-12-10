"""
Record model - stores individual data rows from datasets.

Each record represents one row of data from an uploaded dataset file.
Data is stored in JSONB format for flexible schema support.
"""

from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class Record(BaseModel):
    """
    Record model - represents individual data rows.

    Stores actual data from uploaded datasets in JSONB format.
    Each record belongs to a dataset and includes validation information.
    """

    __tablename__ = "records"

    # Foreign Keys
    dataset_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Dataset this record belongs to"
    )

    # Row Information
    row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Original row position in the uploaded file (1-indexed)"
    )

    # Data Storage
    data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Key-value pairs for each column in the row"
    )

    # Validation
    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether this record passed validation"
    )

    validation_errors: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Array of validation error messages"
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="records"
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_records_dataset_org", "dataset_id", "organization_id"),
        Index("ix_records_dataset_row", "dataset_id", "row_number"),
        Index("ix_records_valid", "dataset_id", "is_valid"),
        {"comment": "Record table for multi-tenant data"},
    )

    def __repr__(self) -> str:
        return f"<Record(id={self.id}, dataset_id={self.dataset_id}, row={self.row_number}, valid={self.is_valid})>"

    @property
    def has_errors(self) -> bool:
        """Check if record has validation errors."""
        return not self.is_valid and self.validation_errors is not None

    @property
    def error_count(self) -> int:
        """Get number of validation errors."""
        if self.validation_errors is None:
            return 0
        return len(self.validation_errors)

    def get_column_value(self, column_name: str, default=None):
        """
        Get value for a specific column.

        Args:
            column_name: Name of the column
            default: Default value if column doesn't exist

        Returns:
            Column value or default
        """
        return self.data.get(column_name, default)

    def set_column_value(self, column_name: str, value):
        """
        Set value for a specific column.

        Args:
            column_name: Name of the column
            value: Value to set
        """
        if self.data is None:
            self.data = {}
        self.data[column_name] = value

    @property
    def column_names(self) -> list[str]:
        """Get list of column names in this record."""
        if self.data is None:
            return []
        return list(self.data.keys())
