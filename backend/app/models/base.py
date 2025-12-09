from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class BaseModel(Base):
    __abstract__ = True

    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, # Some models may not need it but I am requiring it for clarity and safety
        index=True,
        comment="The organization this record belongs to",
    )

    __table_args__ = (
        Index('idx_organization_id_id', 'organization_id', 'id'),
    )

