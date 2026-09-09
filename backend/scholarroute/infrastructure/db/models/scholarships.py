from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from scholarroute.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from scholarroute.infrastructure.db.models.enums import (
    RecordStatus,
    ScholarshipProviderType,
    ScholarshipStatus,
)


class ScholarshipProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_providers"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[ScholarshipProviderType] = mapped_column(
        Enum(ScholarshipProviderType, name="scholarship_provider_type"), nullable=False
    )
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class ScholarshipScheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_schemes"
    __table_args__ = (UniqueConstraint("provider_id", "official_code"),)

    provider_id: Mapped[UUID] = mapped_column(
        ForeignKey("scholarship_providers.id"), nullable=False, index=True
    )
    official_code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class ScholarshipCycle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_cycles"
    __table_args__ = (
        UniqueConstraint("scheme_id", "academic_year", "rule_version"),
        CheckConstraint("academic_year >= 2000 AND academic_year <= 2100", name="year_range"),
        CheckConstraint(
            "application_start_date IS NULL OR deadline IS NULL OR "
            "application_start_date <= deadline",
            name="application_date_order",
        ),
        Index("ix_scholarship_cycles_status_year", "status", "academic_year"),
    )

    scheme_id: Mapped[UUID] = mapped_column(
        ForeignKey("scholarship_schemes.id"), nullable=False, index=True
    )
    academic_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ScholarshipStatus] = mapped_column(
        Enum(ScholarshipStatus, name="scholarship_status"),
        default=ScholarshipStatus.DRAFT,
        nullable=False,
    )
    application_start_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    source_document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_document_versions.id"), nullable=False, index=True
    )


class ScholarshipEligibilityRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_eligibility_rules"
    __table_args__ = (
        CheckConstraint("income_max IS NULL OR income_max >= 0", name="income_non_negative"),
        CheckConstraint(
            "minimum_marks IS NULL OR (minimum_marks >= 0 AND minimum_marks <= 100)",
            name="marks_range",
        ),
        CheckConstraint(
            "achievement_minimum IS NULL OR achievement_minimum >= 0",
            name="achievement_non_negative",
        ),
    )

    cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("scholarship_cycles.id"), unique=True, nullable=False, index=True
    )
    income_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    minimum_marks: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    achievement_code: Mapped[str | None] = mapped_column(String(128))
    achievement_minimum: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    achievement_unit: Mapped[str | None] = mapped_column(String(64))
    conditions_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_locator: Mapped[str | None] = mapped_column(String(500))


class ScholarshipBenefit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_benefits"
    __table_args__ = (
        CheckConstraint("amount_min IS NULL OR amount_min >= 0", name="amount_min_non_negative"),
        CheckConstraint("amount_max IS NULL OR amount_max >= 0", name="amount_max_non_negative"),
        CheckConstraint(
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
            name="amount_order",
        ),
    )

    cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("scholarship_cycles.id"), nullable=False, index=True
    )
    benefit_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    frequency: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, nullable=False)


class ScholarshipRequiredDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scholarship_required_documents"
    __table_args__ = (UniqueConstraint("cycle_id", "document_code"),)

    cycle_id: Mapped[UUID] = mapped_column(
        ForeignKey("scholarship_cycles.id"), nullable=False, index=True
    )
    document_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ScholarshipEligibleState(Base):
    __tablename__ = "scholarship_eligible_states"
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey("scholarship_cycles.id"), primary_key=True)
    state_id: Mapped[UUID] = mapped_column(ForeignKey("states.id"), primary_key=True)


class ScholarshipEligibleProgram(Base):
    __tablename__ = "scholarship_eligible_programs"
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey("scholarship_cycles.id"), primary_key=True)
    program_id: Mapped[UUID] = mapped_column(ForeignKey("programs.id"), primary_key=True)


class ScholarshipEligibleInstitutionType(Base):
    __tablename__ = "scholarship_eligible_institution_types"
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey("scholarship_cycles.id"), primary_key=True)
    institution_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("institution_types.id"), primary_key=True
    )


class ScholarshipEligibleCategory(Base):
    __tablename__ = "scholarship_eligible_categories"
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey("scholarship_cycles.id"), primary_key=True)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), primary_key=True)


class ScholarshipEligibleGenderPool(Base):
    __tablename__ = "scholarship_eligible_gender_pools"
    cycle_id: Mapped[UUID] = mapped_column(ForeignKey("scholarship_cycles.id"), primary_key=True)
    gender_pool_id: Mapped[UUID] = mapped_column(ForeignKey("gender_pools.id"), primary_key=True)
