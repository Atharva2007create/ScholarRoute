from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from scholarroute.infrastructure.db.base import Base, UUIDPrimaryKeyMixin
from scholarroute.infrastructure.db.models.enums import (
    EligibilityStatus,
    EligibilitySubjectType,
    RuleEvaluationStatus,
)


class EligibilityInputSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "eligibility_input_snapshots"
    __table_args__ = (
        CheckConstraint("evaluation_year >= 2000 AND evaluation_year <= 2100", name="year_range"),
        CheckConstraint("length(input_hash) = 64", name="sha256_length"),
        Index("ix_eligibility_snapshots_hash", "input_hash"),
    )

    profile_identifier: Mapped[str | None] = mapped_column(String(255))
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluation_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_input: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EligibilityEvaluation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "eligibility_evaluations"
    __table_args__ = (
        CheckConstraint("evaluation_year >= 2000 AND evaluation_year <= 2100", name="year_range"),
        CheckConstraint("length(rules_hash) = 64", name="rules_sha256_length"),
        Index(
            "ix_eligibility_evaluations_subject_year",
            "subject_type",
            "subject_id",
            "evaluation_year",
        ),
    )

    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("eligibility_input_snapshots.id"), nullable=False, index=True
    )
    subject_type: Mapped[EligibilitySubjectType] = mapped_column(
        Enum(EligibilitySubjectType, name="eligibility_subject_type"), nullable=False
    )
    subject_id: Mapped[UUID] = mapped_column(nullable=False)
    evaluation_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[EligibilityStatus] = mapped_column(
        Enum(EligibilityStatus, name="eligibility_status"), nullable=False
    )
    rule_set_version: Mapped[str] = mapped_column(String(128), nullable=False)
    catalog_release_id: Mapped[UUID | None] = mapped_column(ForeignKey("catalog_releases.id"))
    rules_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    missing_information: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    human_summary: Mapped[str] = mapped_column(Text, nullable=False)


class EligibilityRuleResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "eligibility_rule_results"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "sequence"),
        Index("ix_eligibility_rule_results_rule", "rule_id", "rule_version"),
    )

    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("eligibility_evaluations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("eligibility_rule_results.id"), index=True
    )
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[RuleEvaluationStatus] = mapped_column(
        Enum(RuleEvaluationStatus, name="rule_evaluation_status"), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    observed_value: Mapped[Any | None] = mapped_column(JSON)
    expected_value: Mapped[Any | None] = mapped_column(JSON)
    source_document_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_document_versions.id"), index=True
    )
    source_locator: Mapped[str | None] = mapped_column(String(500))
    official_url: Mapped[str | None] = mapped_column(String(2048))


class EligibilityEvaluationResourceLink(Base):
    __tablename__ = "eligibility_evaluation_resource_links"

    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("eligibility_evaluations.id", ondelete="CASCADE"), primary_key=True
    )
    resource_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("resource_links.id"), primary_key=True
    )
