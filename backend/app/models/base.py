from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

from app.db.base import Base

class BaseModel(Base):
    __abstract__ = True

    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The organization this record belongs to",
    )

    @declared_attr
    def __table_args__(cls):
        return (
            {"comment": f"{cls.__name__} table for multi-tenant data"},
        )

