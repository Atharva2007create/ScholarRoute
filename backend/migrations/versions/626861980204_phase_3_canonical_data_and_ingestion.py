"""phase 3 canonical data and ingestion

Revision ID: 626861980204
Revises: 20260909_0001
Create Date: 2026-09-09 20:21:15.131656
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "626861980204"
down_revision: str | None = "20260909_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

record_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="record_status", create_type=False)
scholarship_provider_type = postgresql.ENUM(
    "CENTRAL_GOVERNMENT",
    "STATE_GOVERNMENT",
    "INSTITUTION",
    "PRIVATE_VERIFIED",
    name="scholarship_provider_type",
    create_type=False,
)
resource_entity_type = postgresql.ENUM(
    "INSTITUTION",
    "PROGRAM",
    "SCHOLARSHIP",
    "COUNSELLING_AUTHORITY",
    "SOURCE_AUTHORITY",
    name="resource_entity_type",
    create_type=False,
)
resource_link_type = postgresql.ENUM(
    "OFFICIAL_WEBSITE",
    "ADMISSIONS_PAGE",
    "COUNSELLING_PAGE",
    "PROGRAM_PAGE",
    "SCHOLARSHIP_PAGE",
    "APPLICATION_PAGE",
    "GUIDELINES_PAGE",
    "SOURCE_DOCUMENT",
    name="resource_link_type",
    create_type=False,
)
scholarship_status = postgresql.ENUM(
    "DRAFT", "OPEN", "CLOSED", "PUBLISHED", "ARCHIVED", name="scholarship_status", create_type=False
)
staged_record_status = postgresql.ENUM(
    "RAW",
    "PARSED",
    "NORMALIZED",
    "VALIDATED",
    "PUBLISHED",
    "REJECTED",
    name="staged_record_status",
    create_type=False,
)
finding_severity = postgresql.ENUM("WARNING", "ERROR", name="finding_severity", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    scholarship_provider_type.create(bind, checkfirst=True)
    resource_entity_type.create(bind, checkfirst=True)
    resource_link_type.create(bind, checkfirst=True)
    scholarship_status.create(bind, checkfirst=True)
    staged_record_status.create(bind, checkfirst=True)
    finding_severity.create(bind, checkfirst=True)
    op.create_table(
        "academic_years",
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "year >= 2000 AND year <= 2100", name=op.f("ck_academic_years_year_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_academic_years")),
        sa.UniqueConstraint("year", name=op.f("uq_academic_years_year")),
    )
    op.create_table(
        "degrees",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_degrees")),
        sa.UniqueConstraint("code", name=op.f("uq_degrees_code")),
    )
    op.create_table(
        "exam_types",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exam_types")),
        sa.UniqueConstraint("code", name=op.f("uq_exam_types_code")),
    )
    op.create_table(
        "gender_pools",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gender_pools")),
        sa.UniqueConstraint("code", name=op.f("uq_gender_pools_code")),
    )
    op.create_table(
        "quota_types",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quota_types")),
        sa.UniqueConstraint("code", name=op.f("uq_quota_types_code")),
    )
    op.create_table(
        "scholarship_providers",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider_type", scholarship_provider_type, nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scholarship_providers")),
        sa.UniqueConstraint("code", name=op.f("uq_scholarship_providers_code")),
    )
    op.create_table(
        "seat_types",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seat_types")),
        sa.UniqueConstraint("code", name=op.f("uq_seat_types_code")),
    )
    op.create_table(
        "source_authorities",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("official_domain", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_authorities")),
        sa.UniqueConstraint("code", name=op.f("uq_source_authorities_code")),
        sa.UniqueConstraint("official_domain", name=op.f("uq_source_authorities_official_domain")),
    )
    op.create_table(
        "subjects",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
        sa.UniqueConstraint("code", name=op.f("uq_subjects_code")),
    )
    op.create_table(
        "scholarship_schemes",
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("official_code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", record_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["scholarship_providers.id"],
            name=op.f("fk_scholarship_schemes_provider_id_scholarship_providers"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scholarship_schemes")),
        sa.UniqueConstraint(
            "provider_id", "official_code", name=op.f("uq_scholarship_schemes_provider_id")
        ),
    )
    op.create_index(
        op.f("ix_scholarship_schemes_provider_id"),
        "scholarship_schemes",
        ["provider_id"],
        unique=False,
    )
    op.create_table(
        "counselling_rounds",
        sa.Column("admission_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sequence", sa.SmallInteger(), nullable=False),
        sa.Column("round_type", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_counselling_rounds_positive_sequence")),
        sa.ForeignKeyConstraint(
            ["admission_cycle_id"],
            ["admission_cycles.id"],
            name=op.f("fk_counselling_rounds_admission_cycle_id_admission_cycles"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_counselling_rounds")),
        sa.UniqueConstraint("admission_cycle_id", "code", name="uq_counselling_round_code"),
        sa.UniqueConstraint("admission_cycle_id", "sequence", name="uq_counselling_round_sequence"),
    )
    op.create_index(
        op.f("ix_counselling_rounds_admission_cycle_id"),
        "counselling_rounds",
        ["admission_cycle_id"],
        unique=False,
    )
    op.create_table(
        "admission_requirements",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("academic_year", sa.SmallInteger(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=True),
        sa.Column("exam_id", sa.Uuid(), nullable=True),
        sa.Column("institution_id", sa.Uuid(), nullable=True),
        sa.Column("program_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("minimum_marks", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "academic_year >= 2000 AND academic_year <= 2100",
            name=op.f("ck_admission_requirements_year_range"),
        ),
        sa.CheckConstraint(
            "minimum_marks IS NULL OR (minimum_marks >= 0 AND minimum_marks <= 100)",
            name=op.f("ck_admission_requirements_marks_range"),
        ),
        sa.ForeignKeyConstraint(
            ["board_id"], ["boards.id"], name=op.f("fk_admission_requirements_board_id_boards")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_admission_requirements_category_id_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["exam_id"], ["exams.id"], name=op.f("fk_admission_requirements_exam_id_exams")
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_admission_requirements_institution_id_institutions"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_admission_requirements_program_id_programs"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name=op.f(
                "fk_admission_requirements_source_document_version_id_source_document_versions"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admission_requirements")),
        sa.UniqueConstraint(
            "code",
            "academic_year",
            "category_id",
            "program_id",
            name="uq_admission_requirement_scope",
        ),
    )
    op.create_index(
        op.f("ix_admission_requirements_academic_year"),
        "admission_requirements",
        ["academic_year"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admission_requirements_board_id"),
        "admission_requirements",
        ["board_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admission_requirements_category_id"),
        "admission_requirements",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admission_requirements_exam_id"),
        "admission_requirements",
        ["exam_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admission_requirements_institution_id"),
        "admission_requirements",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admission_requirements_program_id"),
        "admission_requirements",
        ["program_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admission_requirements_source_document_version_id"),
        "admission_requirements",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_table(
        "fee_schedules",
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=True),
        sa.Column("academic_year", sa.SmallInteger(), nullable=False),
        sa.Column("fee_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=False),
        sa.Column("original_value", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "academic_year >= 2000 AND academic_year <= 2100",
            name=op.f("ck_fee_schedules_year_range"),
        ),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_fee_schedules_amount_non_negative")),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_fee_schedules_institution_id_institutions"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["programs.id"], name=op.f("fk_fee_schedules_program_id_programs")
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name=op.f("fk_fee_schedules_source_document_version_id_source_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fee_schedules")),
        sa.UniqueConstraint(
            "institution_id",
            "program_id",
            "academic_year",
            "fee_type",
            "source_document_version_id",
            name="uq_fee_schedules_evidence",
        ),
    )
    op.create_index(
        op.f("ix_fee_schedules_academic_year"), "fee_schedules", ["academic_year"], unique=False
    )
    op.create_index(
        op.f("ix_fee_schedules_institution_id"), "fee_schedules", ["institution_id"], unique=False
    )
    op.create_index(
        op.f("ix_fee_schedules_program_id"), "fee_schedules", ["program_id"], unique=False
    )
    op.create_index(
        op.f("ix_fee_schedules_source_document_version_id"),
        "fee_schedules",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_table(
        "program_offerings",
        sa.Column("admission_cycle_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("quota_type_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("gender_pool_id", sa.Uuid(), nullable=False),
        sa.Column("seat_type_id", sa.Uuid(), nullable=True),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=False),
        sa.Column("original_values", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admission_cycle_id"],
            ["admission_cycles.id"],
            name=op.f("fk_program_offerings_admission_cycle_id_admission_cycles"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_program_offerings_category_id_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["gender_pool_id"],
            ["gender_pools.id"],
            name=op.f("fk_program_offerings_gender_pool_id_gender_pools"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["programs.id"], name=op.f("fk_program_offerings_program_id_programs")
        ),
        sa.ForeignKeyConstraint(
            ["quota_type_id"],
            ["quota_types.id"],
            name=op.f("fk_program_offerings_quota_type_id_quota_types"),
        ),
        sa.ForeignKeyConstraint(
            ["seat_type_id"],
            ["seat_types.id"],
            name=op.f("fk_program_offerings_seat_type_id_seat_types"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name=op.f("fk_program_offerings_source_document_version_id_source_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_program_offerings")),
        sa.UniqueConstraint(
            "admission_cycle_id",
            "program_id",
            "quota_type_id",
            "category_id",
            "gender_pool_id",
            "seat_type_id",
            name="uq_program_offerings_business_key",
        ),
    )
    op.create_index(
        op.f("ix_program_offerings_admission_cycle_id"),
        "program_offerings",
        ["admission_cycle_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_offerings_category_id"), "program_offerings", ["category_id"], unique=False
    )
    op.create_index(
        op.f("ix_program_offerings_gender_pool_id"),
        "program_offerings",
        ["gender_pool_id"],
        unique=False,
    )
    op.create_index(
        "ix_program_offerings_preselection",
        "program_offerings",
        ["admission_cycle_id", "program_id", "quota_type_id", "category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_offerings_program_id"), "program_offerings", ["program_id"], unique=False
    )
    op.create_index(
        op.f("ix_program_offerings_quota_type_id"),
        "program_offerings",
        ["quota_type_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_offerings_seat_type_id"),
        "program_offerings",
        ["seat_type_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_program_offerings_source_document_version_id"),
        "program_offerings",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_table(
        "resource_links",
        sa.Column("entity_type", resource_entity_type, nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("link_type", resource_link_type, nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("source_authority_id", sa.Uuid(), nullable=False),
        sa.Column("academic_year", sa.SmallInteger(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "academic_year IS NULL OR (academic_year >= 2000 AND academic_year <= 2100)",
            name=op.f("ck_resource_links_year_range"),
        ),
        sa.ForeignKeyConstraint(
            ["source_authority_id"],
            ["source_authorities.id"],
            name=op.f("fk_resource_links_source_authority_id_source_authorities"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name=op.f("fk_resource_links_source_document_version_id_source_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resource_links")),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "link_type",
            "url",
            "academic_year",
            name="uq_resource_links_target_url_year",
        ),
    )
    op.create_index(
        op.f("ix_resource_links_source_authority_id"),
        "resource_links",
        ["source_authority_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_resource_links_source_document_version_id"),
        "resource_links",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_resource_links_target",
        "resource_links",
        ["entity_type", "entity_id", "is_active"],
        unique=False,
    )
    op.create_table(
        "scholarship_cycles",
        sa.Column("scheme_id", sa.Uuid(), nullable=False),
        sa.Column("academic_year", sa.SmallInteger(), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("status", scholarship_status, nullable=False),
        sa.Column("application_start_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "academic_year >= 2000 AND academic_year <= 2100",
            name=op.f("ck_scholarship_cycles_year_range"),
        ),
        sa.CheckConstraint(
            "application_start_date IS NULL OR deadline IS NULL OR "
            "application_start_date <= deadline",
            name=op.f("ck_scholarship_cycles_application_date_order"),
        ),
        sa.ForeignKeyConstraint(
            ["scheme_id"],
            ["scholarship_schemes.id"],
            name=op.f("fk_scholarship_cycles_scheme_id_scholarship_schemes"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name=op.f("fk_scholarship_cycles_source_document_version_id_source_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scholarship_cycles")),
        sa.UniqueConstraint(
            "scheme_id",
            "academic_year",
            "rule_version",
            name=op.f("uq_scholarship_cycles_scheme_id"),
        ),
    )
    op.create_index(
        op.f("ix_scholarship_cycles_scheme_id"), "scholarship_cycles", ["scheme_id"], unique=False
    )
    op.create_index(
        op.f("ix_scholarship_cycles_source_document_version_id"),
        "scholarship_cycles",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_scholarship_cycles_status_year",
        "scholarship_cycles",
        ["status", "academic_year"],
        unique=False,
    )
    op.create_table(
        "admission_requirement_subjects",
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["admission_requirements.id"],
            name=op.f("fk_admission_requirement_subjects_requirement_id_admission_requirements"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name=op.f("fk_admission_requirement_subjects_subject_id_subjects"),
        ),
        sa.PrimaryKeyConstraint(
            "requirement_id", "subject_id", name=op.f("pk_admission_requirement_subjects")
        ),
    )
    op.create_table(
        "cutoff_observations",
        sa.Column("offering_id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("rank_type", sa.String(length=64), nullable=False),
        sa.Column("opening_rank", sa.Integer(), nullable=False),
        sa.Column("closing_rank", sa.Integer(), nullable=False),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=False),
        sa.Column("source_locator", sa.String(length=500), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "closing_rank > 0", name=op.f("ck_cutoff_observations_closing_rank_positive")
        ),
        sa.CheckConstraint(
            "opening_rank <= closing_rank", name=op.f("ck_cutoff_observations_rank_order")
        ),
        sa.CheckConstraint(
            "opening_rank > 0", name=op.f("ck_cutoff_observations_opening_rank_positive")
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["program_offerings.id"],
            name=op.f("fk_cutoff_observations_offering_id_program_offerings"),
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["counselling_rounds.id"],
            name=op.f("fk_cutoff_observations_round_id_counselling_rounds"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name=op.f("fk_cutoff_observations_source_document_version_id_source_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cutoff_observations")),
        sa.UniqueConstraint(
            "offering_id",
            "round_id",
            "rank_type",
            "source_document_version_id",
            name="uq_cutoff_observations_evidence",
        ),
    )
    op.create_index(
        "ix_cutoff_lookup",
        "cutoff_observations",
        ["offering_id", "round_id", "rank_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cutoff_observations_offering_id"),
        "cutoff_observations",
        ["offering_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cutoff_observations_round_id"), "cutoff_observations", ["round_id"], unique=False
    )
    op.create_index(
        op.f("ix_cutoff_observations_source_document_version_id"),
        "cutoff_observations",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_table(
        "scholarship_benefits",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("benefit_type", sa.String(length=64), nullable=False),
        sa.Column("amount_min", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("amount_max", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("frequency", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_max IS NULL OR amount_max >= 0",
            name=op.f("ck_scholarship_benefits_amount_max_non_negative"),
        ),
        sa.CheckConstraint(
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
            name=op.f("ck_scholarship_benefits_amount_order"),
        ),
        sa.CheckConstraint(
            "amount_min IS NULL OR amount_min >= 0",
            name=op.f("ck_scholarship_benefits_amount_min_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_benefits_cycle_id_scholarship_cycles"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scholarship_benefits")),
    )
    op.create_index(
        op.f("ix_scholarship_benefits_cycle_id"), "scholarship_benefits", ["cycle_id"], unique=False
    )
    op.create_table(
        "scholarship_eligibility_rules",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("income_max", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("minimum_marks", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("achievement_code", sa.String(length=128), nullable=True),
        sa.Column("achievement_minimum", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("achievement_unit", sa.String(length=64), nullable=True),
        sa.Column("conditions_summary", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "achievement_minimum IS NULL OR achievement_minimum >= 0",
            name=op.f("ck_scholarship_eligibility_rules_achievement_non_negative"),
        ),
        sa.CheckConstraint(
            "income_max IS NULL OR income_max >= 0",
            name=op.f("ck_scholarship_eligibility_rules_income_non_negative"),
        ),
        sa.CheckConstraint(
            "minimum_marks IS NULL OR (minimum_marks >= 0 AND minimum_marks <= 100)",
            name=op.f("ck_scholarship_eligibility_rules_marks_range"),
        ),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_eligibility_rules_cycle_id_scholarship_cycles"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scholarship_eligibility_rules")),
    )
    op.create_index(
        op.f("ix_scholarship_eligibility_rules_cycle_id"),
        "scholarship_eligibility_rules",
        ["cycle_id"],
        unique=True,
    )
    op.create_table(
        "scholarship_eligible_categories",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_scholarship_eligible_categories_category_id_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_eligible_categories_cycle_id_scholarship_cycles"),
        ),
        sa.PrimaryKeyConstraint(
            "cycle_id", "category_id", name=op.f("pk_scholarship_eligible_categories")
        ),
    )
    op.create_table(
        "scholarship_eligible_gender_pools",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("gender_pool_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_eligible_gender_pools_cycle_id_scholarship_cycles"),
        ),
        sa.ForeignKeyConstraint(
            ["gender_pool_id"],
            ["gender_pools.id"],
            name=op.f("fk_scholarship_eligible_gender_pools_gender_pool_id_gender_pools"),
        ),
        sa.PrimaryKeyConstraint(
            "cycle_id", "gender_pool_id", name=op.f("pk_scholarship_eligible_gender_pools")
        ),
    )
    op.create_table(
        "scholarship_eligible_institution_types",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("institution_type_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_eligible_institution_types_cycle_id_scholarship_cycles"),
        ),
        sa.ForeignKeyConstraint(
            ["institution_type_id"],
            ["institution_types.id"],
            name=op.f(
                "fk_scholarship_eligible_institution_types_institution_type_id_institution_types"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "cycle_id",
            "institution_type_id",
            name=op.f("pk_scholarship_eligible_institution_types"),
        ),
    )
    op.create_table(
        "scholarship_eligible_programs",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_eligible_programs_cycle_id_scholarship_cycles"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_scholarship_eligible_programs_program_id_programs"),
        ),
        sa.PrimaryKeyConstraint(
            "cycle_id", "program_id", name=op.f("pk_scholarship_eligible_programs")
        ),
    )
    op.create_table(
        "scholarship_eligible_states",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_eligible_states_cycle_id_scholarship_cycles"),
        ),
        sa.ForeignKeyConstraint(
            ["state_id"], ["states.id"], name=op.f("fk_scholarship_eligible_states_state_id_states")
        ),
        sa.PrimaryKeyConstraint(
            "cycle_id", "state_id", name=op.f("pk_scholarship_eligible_states")
        ),
    )
    op.create_table(
        "scholarship_required_documents",
        sa.Column("cycle_id", sa.Uuid(), nullable=False),
        sa.Column("document_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cycle_id"],
            ["scholarship_cycles.id"],
            name=op.f("fk_scholarship_required_documents_cycle_id_scholarship_cycles"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scholarship_required_documents")),
        sa.UniqueConstraint(
            "cycle_id", "document_code", name=op.f("uq_scholarship_required_documents_cycle_id")
        ),
    )
    op.create_index(
        op.f("ix_scholarship_required_documents_cycle_id"),
        "scholarship_required_documents",
        ["cycle_id"],
        unique=False,
    )
    op.create_table(
        "seat_matrix_entries",
        sa.Column("offering_id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=True),
        sa.Column("seat_count", sa.Integer(), nullable=False),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=False),
        sa.Column("source_locator", sa.String(length=500), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "seat_count >= 0", name=op.f("ck_seat_matrix_entries_seat_count_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["program_offerings.id"],
            name=op.f("fk_seat_matrix_entries_offering_id_program_offerings"),
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["counselling_rounds.id"],
            name=op.f("fk_seat_matrix_entries_round_id_counselling_rounds"),
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name=op.f("fk_seat_matrix_entries_source_document_version_id_source_document_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seat_matrix_entries")),
        sa.UniqueConstraint(
            "offering_id", "round_id", "source_document_version_id", name="uq_seat_matrix_evidence"
        ),
    )
    op.create_index(
        op.f("ix_seat_matrix_entries_offering_id"),
        "seat_matrix_entries",
        ["offering_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_seat_matrix_entries_round_id"), "seat_matrix_entries", ["round_id"], unique=False
    )
    op.create_index(
        op.f("ix_seat_matrix_entries_source_document_version_id"),
        "seat_matrix_entries",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_table(
        "staged_records",
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("record_key", sa.String(length=255), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=True),
        sa.Column("source_locator", sa.String(length=500), nullable=False),
        sa.Column("status", staged_record_status, nullable=False),
        sa.Column("published_entity_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_staged_records_ingestion_run_id_ingestion_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staged_records")),
        sa.UniqueConstraint(
            "ingestion_run_id", "record_key", name=op.f("uq_staged_records_ingestion_run_id")
        ),
    )
    op.create_index(
        op.f("ix_staged_records_ingestion_run_id"),
        "staged_records",
        ["ingestion_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_staged_records_run_status",
        "staged_records",
        ["ingestion_run_id", "status"],
        unique=False,
    )
    op.create_table(
        "validation_findings",
        sa.Column("staged_record_id", sa.Uuid(), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("severity", finding_severity, nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["staged_record_id"],
            ["staged_records.id"],
            name=op.f("fk_validation_findings_staged_record_id_staged_records"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_findings")),
    )
    op.create_index(
        "ix_validation_findings_record_severity",
        "validation_findings",
        ["staged_record_id", "severity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_validation_findings_staged_record_id"),
        "validation_findings",
        ["staged_record_id"],
        unique=False,
    )
    op.add_column("data_sources", sa.Column("authority_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_data_sources_authority_id"), "data_sources", ["authority_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_data_sources_authority_id_source_authorities"),
        "data_sources",
        "source_authorities",
        ["authority_id"],
        ["id"],
    )
    op.add_column("exams", sa.Column("exam_type_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_exams_exam_type_id"), "exams", ["exam_type_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_exams_exam_type_id_exam_types"), "exams", "exam_types", ["exam_type_id"], ["id"]
    )
    op.add_column(
        "ingestion_runs", sa.Column("source_document_version_id", sa.Uuid(), nullable=True)
    )
    op.add_column("ingestion_runs", sa.Column("academic_year", sa.SmallInteger(), nullable=True))
    op.add_column(
        "ingestion_runs", sa.Column("source_filename", sa.String(length=500), nullable=True)
    )
    op.add_column("ingestion_runs", sa.Column("checksum", sa.String(length=64), nullable=True))
    op.add_column(
        "ingestion_runs",
        sa.Column("records_discovered", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("records_parsed", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("records_validated", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("records_published", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("records_rejected", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        op.f("ix_ingestion_runs_source_document_version_id"),
        "ingestion_runs",
        ["source_document_version_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_ingestion_runs_source_document_version_id_source_document_versions"),
        "ingestion_runs",
        "source_document_versions",
        ["source_document_version_id"],
        ["id"],
    )
    op.add_column(
        "institutions", sa.Column("official_identifier", sa.String(length=128), nullable=True)
    )
    op.add_column("institutions", sa.Column("ownership_type", sa.String(length=64), nullable=True))
    op.add_column("programs", sa.Column("degree_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_programs_degree_id"), "programs", ["degree_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_programs_degree_id_degrees"), "programs", "degrees", ["degree_id"], ["id"]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f("fk_programs_degree_id_degrees"), "programs", type_="foreignkey")
    op.drop_index(op.f("ix_programs_degree_id"), table_name="programs")
    op.drop_column("programs", "degree_id")
    op.drop_column("institutions", "ownership_type")
    op.drop_column("institutions", "official_identifier")
    op.drop_constraint(
        op.f("fk_ingestion_runs_source_document_version_id_source_document_versions"),
        "ingestion_runs",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_ingestion_runs_source_document_version_id"), table_name="ingestion_runs")
    op.drop_column("ingestion_runs", "records_rejected")
    op.drop_column("ingestion_runs", "records_published")
    op.drop_column("ingestion_runs", "records_validated")
    op.drop_column("ingestion_runs", "records_parsed")
    op.drop_column("ingestion_runs", "records_discovered")
    op.drop_column("ingestion_runs", "checksum")
    op.drop_column("ingestion_runs", "source_filename")
    op.drop_column("ingestion_runs", "academic_year")
    op.drop_column("ingestion_runs", "source_document_version_id")
    op.drop_constraint(op.f("fk_exams_exam_type_id_exam_types"), "exams", type_="foreignkey")
    op.drop_index(op.f("ix_exams_exam_type_id"), table_name="exams")
    op.drop_column("exams", "exam_type_id")
    op.drop_constraint(
        op.f("fk_data_sources_authority_id_source_authorities"), "data_sources", type_="foreignkey"
    )
    op.drop_index(op.f("ix_data_sources_authority_id"), table_name="data_sources")
    op.drop_column("data_sources", "authority_id")
    op.drop_index(op.f("ix_validation_findings_staged_record_id"), table_name="validation_findings")
    op.drop_index("ix_validation_findings_record_severity", table_name="validation_findings")
    op.drop_table("validation_findings")
    op.drop_index("ix_staged_records_run_status", table_name="staged_records")
    op.drop_index(op.f("ix_staged_records_ingestion_run_id"), table_name="staged_records")
    op.drop_table("staged_records")
    op.drop_index(
        op.f("ix_seat_matrix_entries_source_document_version_id"), table_name="seat_matrix_entries"
    )
    op.drop_index(op.f("ix_seat_matrix_entries_round_id"), table_name="seat_matrix_entries")
    op.drop_index(op.f("ix_seat_matrix_entries_offering_id"), table_name="seat_matrix_entries")
    op.drop_table("seat_matrix_entries")
    op.drop_index(
        op.f("ix_scholarship_required_documents_cycle_id"),
        table_name="scholarship_required_documents",
    )
    op.drop_table("scholarship_required_documents")
    op.drop_table("scholarship_eligible_states")
    op.drop_table("scholarship_eligible_programs")
    op.drop_table("scholarship_eligible_institution_types")
    op.drop_table("scholarship_eligible_gender_pools")
    op.drop_table("scholarship_eligible_categories")
    op.drop_index(
        op.f("ix_scholarship_eligibility_rules_cycle_id"),
        table_name="scholarship_eligibility_rules",
    )
    op.drop_table("scholarship_eligibility_rules")
    op.drop_index(op.f("ix_scholarship_benefits_cycle_id"), table_name="scholarship_benefits")
    op.drop_table("scholarship_benefits")
    op.drop_index(
        op.f("ix_cutoff_observations_source_document_version_id"), table_name="cutoff_observations"
    )
    op.drop_index(op.f("ix_cutoff_observations_round_id"), table_name="cutoff_observations")
    op.drop_index(op.f("ix_cutoff_observations_offering_id"), table_name="cutoff_observations")
    op.drop_index("ix_cutoff_lookup", table_name="cutoff_observations")
    op.drop_table("cutoff_observations")
    op.drop_table("admission_requirement_subjects")
    op.drop_index("ix_scholarship_cycles_status_year", table_name="scholarship_cycles")
    op.drop_index(
        op.f("ix_scholarship_cycles_source_document_version_id"), table_name="scholarship_cycles"
    )
    op.drop_index(op.f("ix_scholarship_cycles_scheme_id"), table_name="scholarship_cycles")
    op.drop_table("scholarship_cycles")
    op.drop_index("ix_resource_links_target", table_name="resource_links")
    op.drop_index(op.f("ix_resource_links_source_document_version_id"), table_name="resource_links")
    op.drop_index(op.f("ix_resource_links_source_authority_id"), table_name="resource_links")
    op.drop_table("resource_links")
    op.drop_index(
        op.f("ix_program_offerings_source_document_version_id"), table_name="program_offerings"
    )
    op.drop_index(op.f("ix_program_offerings_seat_type_id"), table_name="program_offerings")
    op.drop_index(op.f("ix_program_offerings_quota_type_id"), table_name="program_offerings")
    op.drop_index(op.f("ix_program_offerings_program_id"), table_name="program_offerings")
    op.drop_index("ix_program_offerings_preselection", table_name="program_offerings")
    op.drop_index(op.f("ix_program_offerings_gender_pool_id"), table_name="program_offerings")
    op.drop_index(op.f("ix_program_offerings_category_id"), table_name="program_offerings")
    op.drop_index(op.f("ix_program_offerings_admission_cycle_id"), table_name="program_offerings")
    op.drop_table("program_offerings")
    op.drop_index(op.f("ix_fee_schedules_source_document_version_id"), table_name="fee_schedules")
    op.drop_index(op.f("ix_fee_schedules_program_id"), table_name="fee_schedules")
    op.drop_index(op.f("ix_fee_schedules_institution_id"), table_name="fee_schedules")
    op.drop_index(op.f("ix_fee_schedules_academic_year"), table_name="fee_schedules")
    op.drop_table("fee_schedules")
    op.drop_index(
        op.f("ix_admission_requirements_source_document_version_id"),
        table_name="admission_requirements",
    )
    op.drop_index(op.f("ix_admission_requirements_program_id"), table_name="admission_requirements")
    op.drop_index(
        op.f("ix_admission_requirements_institution_id"), table_name="admission_requirements"
    )
    op.drop_index(op.f("ix_admission_requirements_exam_id"), table_name="admission_requirements")
    op.drop_index(
        op.f("ix_admission_requirements_category_id"), table_name="admission_requirements"
    )
    op.drop_index(op.f("ix_admission_requirements_board_id"), table_name="admission_requirements")
    op.drop_index(
        op.f("ix_admission_requirements_academic_year"), table_name="admission_requirements"
    )
    op.drop_table("admission_requirements")
    op.drop_index(op.f("ix_counselling_rounds_admission_cycle_id"), table_name="counselling_rounds")
    op.drop_table("counselling_rounds")
    op.drop_index(op.f("ix_scholarship_schemes_provider_id"), table_name="scholarship_schemes")
    op.drop_table("scholarship_schemes")
    op.drop_table("subjects")
    op.drop_table("source_authorities")
    op.drop_table("seat_types")
    op.drop_table("scholarship_providers")
    op.drop_table("quota_types")
    op.drop_table("gender_pools")
    op.drop_table("exam_types")
    op.drop_table("degrees")
    op.drop_table("academic_years")
    bind = op.get_bind()
    finding_severity.drop(bind, checkfirst=True)
    staged_record_status.drop(bind, checkfirst=True)
    scholarship_status.drop(bind, checkfirst=True)
    resource_link_type.drop(bind, checkfirst=True)
    resource_entity_type.drop(bind, checkfirst=True)
    scholarship_provider_type.drop(bind, checkfirst=True)
