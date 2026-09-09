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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scholarroute.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from scholarroute.infrastructure.db.models.enums import (
    AdmissionCycleStatus,
    RecordStatus,
    ReleaseStatus,
)


class CodedReferenceMixin(UUIDPrimaryKeyMixin, TimestampMixin):
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class Exam(CodedReferenceMixin, Base):
    __tablename__ = "exams"

    exam_type_id: Mapped[UUID | None] = mapped_column(ForeignKey("exam_types.id"), index=True)


class ExamType(CodedReferenceMixin, Base):
    __tablename__ = "exam_types"


class Board(CodedReferenceMixin, Base):
    __tablename__ = "boards"


class State(CodedReferenceMixin, Base):
    __tablename__ = "states"

    country_code: Mapped[str] = mapped_column(String(2), default="IN", nullable=False)


class Category(CodedReferenceMixin, Base):
    __tablename__ = "categories"


class InstitutionType(CodedReferenceMixin, Base):
    __tablename__ = "institution_types"


class Course(CodedReferenceMixin, Base):
    __tablename__ = "courses"


class Branch(CodedReferenceMixin, Base):
    __tablename__ = "branches"

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    course: Mapped[Course] = relationship()


class Degree(CodedReferenceMixin, Base):
    __tablename__ = "degrees"


class Subject(CodedReferenceMixin, Base):
    __tablename__ = "subjects"


class QuotaType(CodedReferenceMixin, Base):
    __tablename__ = "quota_types"


class GenderPool(CodedReferenceMixin, Base):
    __tablename__ = "gender_pools"


class SeatType(CodedReferenceMixin, Base):
    __tablename__ = "seat_types"


class AcademicYear(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academic_years"
    __table_args__ = (CheckConstraint("year >= 2000 AND year <= 2100", name="year_range"),)

    year: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )


class Institution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "institutions"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    official_name: Mapped[str] = mapped_column(String(255), nullable=False)
    institution_type_id: Mapped[UUID] = mapped_column(
        ForeignKey("institution_types.id"), nullable=False, index=True
    )
    state_id: Mapped[UUID] = mapped_column(ForeignKey("states.id"), nullable=False, index=True)
    official_url: Mapped[str | None] = mapped_column(String(2048))
    official_identifier: Mapped[str | None] = mapped_column(String(128))
    ownership_type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )

    institution_type: Mapped[InstitutionType] = relationship()
    state: Mapped[State] = relationship()
    campuses: Mapped[list[Campus]] = relationship(back_populates="institution")
    programs: Mapped[list[Program]] = relationship(back_populates="institution")


class Campus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "campuses"
    __table_args__ = (UniqueConstraint("institution_id", "code"),)

    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id"), nullable=False, index=True
    )
    state_id: Mapped[UUID] = mapped_column(ForeignKey("states.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)

    institution: Mapped[Institution] = relationship(back_populates="campuses")
    state: Mapped[State] = relationship()


class Program(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("institution_id", "code"),)

    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id"), nullable=False, index=True
    )
    campus_id: Mapped[UUID | None] = mapped_column(ForeignKey("campuses.id"), index=True)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    branch_id: Mapped[UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    degree_id: Mapped[UUID | None] = mapped_column(ForeignKey("degrees.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )

    institution: Mapped[Institution] = relationship(back_populates="programs")
    campus: Mapped[Campus | None] = relationship()
    course: Mapped[Course] = relationship()
    branch: Mapped[Branch | None] = relationship()
    degree: Mapped[Degree | None] = relationship()


class CounsellingAuthority(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "counselling_authorities"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    official_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    state_id: Mapped[UUID | None] = mapped_column(ForeignKey("states.id"), index=True)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"), default=RecordStatus.ACTIVE, nullable=False
    )

    state: Mapped[State | None] = relationship()


class CatalogRelease(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "catalog_releases"
    __table_args__ = (
        UniqueConstraint("domain", "academic_year", "version"),
        CheckConstraint(
            "academic_year >= 2000 AND academic_year <= 2100", name="academic_year_range"
        ),
        Index(
            "uq_catalog_releases_published_scope",
            "domain",
            "academic_year",
            unique=True,
            postgresql_where=text("status = 'PUBLISHED'"),
        ),
    )

    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    academic_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ReleaseStatus] = mapped_column(
        Enum(ReleaseStatus, name="release_status"), default=ReleaseStatus.DRAFT, nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdmissionCycle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admission_cycles"
    __table_args__ = (
        UniqueConstraint("authority_id", "exam_id", "academic_year", "scope_state_id"),
        CheckConstraint(
            "academic_year >= 2000 AND academic_year <= 2100", name="academic_year_range"
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date", name="date_order"
        ),
    )

    authority_id: Mapped[UUID] = mapped_column(
        ForeignKey("counselling_authorities.id"), nullable=False, index=True
    )
    exam_id: Mapped[UUID] = mapped_column(ForeignKey("exams.id"), nullable=False, index=True)
    academic_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    scope_state_id: Mapped[UUID | None] = mapped_column(ForeignKey("states.id"), index=True)
    catalog_release_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("catalog_releases.id"), index=True
    )
    status: Mapped[AdmissionCycleStatus] = mapped_column(
        Enum(AdmissionCycleStatus, name="admission_cycle_status"),
        default=AdmissionCycleStatus.DRAFT,
        nullable=False,
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    authority: Mapped[CounsellingAuthority] = relationship()
    exam: Mapped[Exam] = relationship()
    scope_state: Mapped[State | None] = relationship()
    catalog_release: Mapped[CatalogRelease | None] = relationship()
