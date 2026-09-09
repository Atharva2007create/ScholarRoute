from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from scholarroute.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from scholarroute.infrastructure.db.models.enums import ResourceEntityType, ResourceLinkType


class ResourceLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resource_links"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "link_type",
            "url",
            "academic_year",
            name="uq_resource_links_target_url_year",
        ),
        CheckConstraint(
            "academic_year IS NULL OR (academic_year >= 2000 AND academic_year <= 2100)",
            name="year_range",
        ),
        Index("ix_resource_links_target", "entity_type", "entity_id", "is_active"),
    )

    entity_type: Mapped[ResourceEntityType] = mapped_column(
        Enum(ResourceEntityType, name="resource_entity_type"), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    link_type: Mapped[ResourceLinkType] = mapped_column(
        Enum(ResourceLinkType, name="resource_link_type"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_authority_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_authorities.id"), nullable=False, index=True
    )
    academic_year: Mapped[int | None] = mapped_column(SmallInteger)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_document_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_document_versions.id"), index=True
    )
