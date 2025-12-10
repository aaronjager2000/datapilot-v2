# Creates the declarative base for all of the SQLAlchemy models to inherit from. Parent class for all the database tables

#This file creates the base class, defines common fields and sets up SQLAlchemy 2.0 async pattern

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime, func
from sqlalchemy import String

from datetime import datetime
from typing import Any, Optional
from uuid import UUID as PyUUID,uuid4

class Base(DeclarativeBase):
    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
        comment="Unique identifier for this record")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the record was created")
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when this record was last updated"
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when this record was soft-deleted (NULL if not deleted)"
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def dict(self) -> dict[str, Any]:
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
