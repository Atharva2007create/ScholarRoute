from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from scholarroute.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A verified media attachment for a canonical institution or provider."""

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('INSTITUTION', 'SCHOLARSHIP_PROVIDER')",
            name="entity_type_supported",
        ),
        CheckConstraint(
            "media_type IN ('LOGO', 'CAMPUS_IMAGE', 'SCHEME_LOGO')",
            name="media_type_supported",
        ),
        CheckConstraint("validation_status = 'VERIFIED'", name="verified_only"),
        UniqueConstraint("entity_type", "entity_id", "media_type"),
        Index("ix_media_assets_entity", "entity_type", "entity_id"),
    )

    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    official_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(32), default="VERIFIED", nullable=False
    )
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    content_length: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    usage_note: Mapped[str | None] = mapped_column(String(500))
