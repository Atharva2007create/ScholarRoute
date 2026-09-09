from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scholarroute.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from scholarroute.infrastructure.db.models.catalog import CatalogRelease
from scholarroute.infrastructure.db.models.enums import DataSourceType, IngestionRunStatus


class DataSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint("trust_tier >= 1 AND trust_tier <= 5", name="trust_tier_range"),
    )

    authority_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    source_type: Mapped[DataSourceType] = mapped_column(
        Enum(DataSourceType, name="data_source_type"), nullable=False
    )
    trust_tier: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    retrieval_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    documents: Mapped[list[SourceDocument]] = relationship(back_populates="data_source")


class SourceDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("data_source_id", "canonical_uri"),
        CheckConstraint(
            "academic_year IS NULL OR (academic_year >= 2000 AND academic_year <= 2100)",
            name="academic_year_range",
        ),
    )

    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id"), nullable=False, index=True
    )
    canonical_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date)
    academic_year: Mapped[int | None] = mapped_column(SmallInteger)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)

    data_source: Mapped[DataSource] = relationship(back_populates="documents")
    versions: Mapped[list[SourceDocumentVersion]] = relationship(
        back_populates="document", foreign_keys="SourceDocumentVersion.document_id"
    )


class SourceDocumentVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "source_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "content_hash"),
        CheckConstraint("length(content_hash) = 64", name="sha256_length"),
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id"), nullable=False, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    http_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(64))
    supersedes_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_document_versions.id", name="fk_source_version_supersedes"), index=True
    )

    document: Mapped[SourceDocument] = relationship(
        back_populates="versions", foreign_keys=[document_id]
    )
    supersedes: Mapped[SourceDocumentVersion | None] = relationship(
        remote_side="SourceDocumentVersion.id", foreign_keys=[supersedes_id]
    )


class IngestionRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at", name="completion_order"
        ),
        Index("ix_ingestion_runs_source_started", "data_source_id", "started_at"),
    )

    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_version: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[IngestionRunStatus] = mapped_column(
        Enum(IngestionRunStatus, name="ingestion_run_status"),
        default=IngestionRunStatus.RECEIVED,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)

    data_source: Mapped[DataSource] = relationship()


class ReleaseSourceVersion(Base):
    __tablename__ = "release_source_versions"

    catalog_release_id: Mapped[UUID] = mapped_column(
        ForeignKey("catalog_releases.id"), primary_key=True
    )
    source_document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_document_versions.id", name="fk_release_source_document_version"),
        primary_key=True,
    )

    catalog_release: Mapped[CatalogRelease] = relationship()
    source_document_version: Mapped[SourceDocumentVersion] = relationship()
