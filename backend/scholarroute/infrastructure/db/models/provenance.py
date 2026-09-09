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
from scholarroute.infrastructure.db.models.enums import (
    DataSourceType,
    FindingSeverity,
    IngestionRunStatus,
    RecordStatus,
    StagedRecordStatus,
)


class SourceAuthority(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_authorities"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    official_domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class DataSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint("trust_tier >= 1 AND trust_tier <= 5", name="trust_tier_range"),
    )

    authority_name: Mapped[str] = mapped_column(String(255), nullable=False)
    authority_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_authorities.id"), index=True
    )
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
    source_document_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_document_versions.id"), index=True
    )
    academic_year: Mapped[int | None] = mapped_column(SmallInteger)
    source_filename: Mapped[str | None] = mapped_column(String(500))
    checksum: Mapped[str | None] = mapped_column(String(64))
    records_discovered: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    records_parsed: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    records_validated: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    records_published: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    records_rejected: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
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


class StagedRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staged_records"
    __table_args__ = (
        UniqueConstraint("ingestion_run_id", "record_key"),
        Index("ix_staged_records_run_status", "ingestion_run_id", "status"),
    )

    ingestion_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    record_key: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    normalized_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source_locator: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[StagedRecordStatus] = mapped_column(
        Enum(StagedRecordStatus, name="staged_record_status"),
        default=StagedRecordStatus.RAW,
        nullable=False,
    )
    published_entity_id: Mapped[UUID | None] = mapped_column()


class ValidationFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "validation_findings"
    __table_args__ = (
        Index("ix_validation_findings_record_severity", "staged_record_id", "severity"),
    )

    staged_record_id: Mapped[UUID] = mapped_column(
        ForeignKey("staged_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity"), nullable=False
    )
    field_name: Mapped[str | None] = mapped_column(String(128))
    message: Mapped[str] = mapped_column(Text, nullable=False)


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
