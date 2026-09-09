from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from scholarroute.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CounsellingRound(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "counselling_rounds"
    __table_args__ = (
        UniqueConstraint("admission_cycle_id", "code", name="uq_counselling_round_code"),
        UniqueConstraint("admission_cycle_id", "sequence", name="uq_counselling_round_sequence"),
        CheckConstraint("sequence > 0", name="positive_sequence"),
    )

    admission_cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("admission_cycles.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    round_type: Mapped[str] = mapped_column(String(64), default="ALLOTMENT", nullable=False)


class ProgramOffering(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "program_offerings"
    __table_args__ = (
        UniqueConstraint(
            "admission_cycle_id",
            "program_id",
            "quota_type_id",
            "category_id",
            "gender_pool_id",
            "seat_type_id",
            name="uq_program_offerings_business_key",
        ),
        Index(
            "ix_program_offerings_preselection",
            "admission_cycle_id",
            "program_id",
            "quota_type_id",
            "category_id",
        ),
    )

    admission_cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("admission_cycles.id"), nullable=False, index=True
    )
    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id"), nullable=False, index=True)
    quota_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("quota_types.id"), nullable=False, index=True
    )
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id"), nullable=False, index=True
    )
    gender_pool_id: Mapped[UUID] = mapped_column(
        ForeignKey("gender_pools.id"), nullable=False, index=True
    )
    seat_type_id: Mapped[UUID | None] = mapped_column(ForeignKey("seat_types.id"), index=True)
    source_document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=False, index=True
    )
    original_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class CutoffObservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cutoff_observations"
    __table_args__ = (
        UniqueConstraint(
            "offering_id",
            "round_id",
            "rank_type",
            "source_document_version_id",
            name="uq_cutoff_observations_evidence",
        ),
        CheckConstraint("opening_rank > 0", name="opening_rank_positive"),
        CheckConstraint("closing_rank > 0", name="closing_rank_positive"),
        CheckConstraint("opening_rank <= closing_rank", name="rank_order"),
        Index("ix_cutoff_lookup", "offering_id", "round_id", "rank_type"),
    )

    offering_id: Mapped[UUID] = mapped_column(
        ForeignKey("program_offerings.id"), nullable=False, index=True
    )
    round_id: Mapped[UUID] = mapped_column(
        ForeignKey("counselling_rounds.id"), nullable=False, index=True
    )
    rank_type: Mapped[str] = mapped_column(String(64), nullable=False)
    opening_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    closing_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    source_document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=False, index=True
    )
    source_locator: Mapped[str] = mapped_column(String(500), nullable=False)


class SeatMatrixEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "seat_matrix_entries"
    __table_args__ = (
        UniqueConstraint(
            "offering_id", "round_id", "source_document_version_id", name="uq_seat_matrix_evidence"
        ),
        CheckConstraint("seat_count >= 0", name="seat_count_non_negative"),
    )

    offering_id: Mapped[UUID] = mapped_column(
        ForeignKey("program_offerings.id"), nullable=False, index=True
    )
    round_id: Mapped[UUID | None] = mapped_column(ForeignKey("counselling_rounds.id"), index=True)
    seat_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=False, index=True
    )
    source_locator: Mapped[str] = mapped_column(String(500), nullable=False)


class FeeSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fee_schedules"
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "program_id",
            "academic_year",
            "fee_type",
            "source_document_version_id",
            name="uq_fee_schedules_evidence",
        ),
        CheckConstraint("academic_year >= 2000 AND academic_year <= 2100", name="year_range"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id"), nullable=False, index=True
    )
    program_id: Mapped[UUID | None] = mapped_column(ForeignKey("programs.id"), index=True)
    academic_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    fee_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    source_document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=False, index=True
    )
    original_value: Mapped[str | None] = mapped_column(String(255))


class AdmissionRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admission_requirements"
    __table_args__ = (
        CheckConstraint("academic_year >= 2000 AND academic_year <= 2100", name="year_range"),
        CheckConstraint(
            "minimum_marks IS NULL OR (minimum_marks >= 0 AND minimum_marks <= 100)",
            name="marks_range",
        ),
        CheckConstraint(
            "minimum_exam_score IS NULL OR minimum_exam_score >= 0",
            name="exam_score_non_negative",
        ),
        CheckConstraint(
            "maximum_exam_rank IS NULL OR maximum_exam_rank > 0",
            name="exam_rank_positive",
        ),
        CheckConstraint(
            "minimum_age IS NULL OR minimum_age >= 0",
            name="minimum_age_non_negative",
        ),
        CheckConstraint(
            "maximum_age IS NULL OR maximum_age >= 0",
            name="maximum_age_non_negative",
        ),
        CheckConstraint(
            "minimum_age IS NULL OR maximum_age IS NULL OR minimum_age <= maximum_age",
            name="age_order",
        ),
        UniqueConstraint(
            "code",
            "academic_year",
            "category_id",
            "institution_id",
            "program_id",
            "rule_version",
            name="uq_admission_requirement_scope",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    academic_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    board_id: Mapped[UUID | None] = mapped_column(ForeignKey("boards.id"), index=True)
    exam_id: Mapped[UUID | None] = mapped_column(ForeignKey("exams.id"), index=True)
    institution_id: Mapped[UUID | None] = mapped_column(ForeignKey("institutions.id"), index=True)
    program_id: Mapped[UUID | None] = mapped_column(ForeignKey("programs.id"), index=True)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), index=True)
    domicile_state_id: Mapped[UUID | None] = mapped_column(ForeignKey("states.id"), index=True)
    gender_pool_id: Mapped[UUID | None] = mapped_column(ForeignKey("gender_pools.id"), index=True)
    quota_type_id: Mapped[UUID | None] = mapped_column(ForeignKey("quota_types.id"), index=True)
    minimum_marks: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    minimum_exam_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    maximum_exam_rank: Mapped[int | None] = mapped_column(Integer)
    minimum_age: Mapped[int | None] = mapped_column(SmallInteger)
    maximum_age: Mapped[int | None] = mapped_column(SmallInteger)
    required_pwd: Mapped[bool | None] = mapped_column(Boolean)
    required_ews: Mapped[bool | None] = mapped_column(Boolean)
    nationality_code: Mapped[str | None] = mapped_column(String(16))
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str | None] = mapped_column(String(500))
    source_document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=False, index=True
    )


class AdmissionRequirementSubject(Base):
    __tablename__ = "admission_requirement_subjects"
    __table_args__ = (
        CheckConstraint(
            "minimum_marks IS NULL OR (minimum_marks >= 0 AND minimum_marks <= 100)",
            name="marks_range",
        ),
    )

    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("admission_requirements.id"), primary_key=True
    )
    subject_id: Mapped[UUID] = mapped_column(ForeignKey("subjects.id"), primary_key=True)
    minimum_marks: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
