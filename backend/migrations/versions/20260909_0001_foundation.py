"""Create the foundational catalog and provenance schema.

Revision ID: 20260909_0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

record_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="record_status", create_type=False)
admission_cycle_status = postgresql.ENUM(
    "DRAFT", "OPEN", "CLOSED", "ARCHIVED", name="admission_cycle_status", create_type=False
)
release_status = postgresql.ENUM(
    "DRAFT",
    "APPROVED",
    "PUBLISHED",
    "REJECTED",
    "SUPERSEDED",
    name="release_status",
    create_type=False,
)
data_source_type = postgresql.ENUM(
    "API", "WEB_PAGE", "DOCUMENT", "DATASET", name="data_source_type", create_type=False
)
ingestion_run_status = postgresql.ENUM(
    "RECEIVED",
    "PARSED",
    "VALIDATION_FAILED",
    "REVIEW_REQUIRED",
    "APPROVED",
    "PUBLISHED",
    "REJECTED",
    "SUPERSEDED",
    name="ingestion_run_status",
    create_type=False,
)


def _reference_table(name: str, *, state: bool = False) -> None:
    columns: list[sa.Column[object]] = [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", record_status, server_default="ACTIVE", nullable=False),
    ]
    if state:
        columns.append(
            sa.Column("country_code", sa.String(length=2), server_default="IN", nullable=False)
        )
    columns.extend(
        [
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id", name=f"pk_{name}"),
            sa.UniqueConstraint("code", name=f"uq_{name}_code"),
        ]
    )
    op.create_table(name, *columns)


def upgrade() -> None:
    bind = op.get_bind()
    record_status.create(bind, checkfirst=True)
    admission_cycle_status.create(bind, checkfirst=True)
    release_status.create(bind, checkfirst=True)
    data_source_type.create(bind, checkfirst=True)
    ingestion_run_status.create(bind, checkfirst=True)

    _reference_table("exams")
    _reference_table("boards")
    _reference_table("states", state=True)
    _reference_table("categories")
    _reference_table("institution_types")
    _reference_table("courses")

    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", record_status, server_default="ACTIVE", nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name="fk_branches_course_id_courses"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_branches"),
        sa.UniqueConstraint("code", name="uq_branches_code"),
    )
    op.create_index("ix_branches_course_id", "branches", ["course_id"])

    op.create_table(
        "institutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("official_name", sa.String(255), nullable=False),
        sa.Column("institution_type_id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=False),
        sa.Column("official_url", sa.String(2048)),
        sa.Column("status", record_status, server_default="ACTIVE", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["institution_type_id"],
            ["institution_types.id"],
            name="fk_institutions_institution_type_id_institution_types",
        ),
        sa.ForeignKeyConstraint(
            ["state_id"], ["states.id"], name="fk_institutions_state_id_states"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_institutions"),
        sa.UniqueConstraint("code", name="uq_institutions_code"),
    )
    op.create_index("ix_institutions_institution_type_id", "institutions", ["institution_type_id"])
    op.create_index("ix_institutions_state_id", "institutions", ["state_id"])

    op.create_table(
        "campuses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name="fk_campuses_institution_id_institutions"
        ),
        sa.ForeignKeyConstraint(["state_id"], ["states.id"], name="fk_campuses_state_id_states"),
        sa.PrimaryKeyConstraint("id", name="pk_campuses"),
        sa.UniqueConstraint("institution_id", "code", name="uq_campuses_institution_id"),
    )
    op.create_index("ix_campuses_institution_id", "campuses", ["institution_id"])
    op.create_index("ix_campuses_state_id", "campuses", ["state_id"])

    op.create_table(
        "programs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("campus_id", sa.Uuid()),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid()),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", record_status, server_default="ACTIVE", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name="fk_programs_institution_id_institutions"
        ),
        sa.ForeignKeyConstraint(
            ["campus_id"], ["campuses.id"], name="fk_programs_campus_id_campuses"
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name="fk_programs_course_id_courses"
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], name="fk_programs_branch_id_branches"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_programs"),
        sa.UniqueConstraint("institution_id", "code", name="uq_programs_institution_id"),
    )
    for column in ("institution_id", "campus_id", "course_id", "branch_id"):
        op.create_index(f"ix_programs_{column}", "programs", [column])

    op.create_table(
        "counselling_authorities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("official_url", sa.String(2048), nullable=False),
        sa.Column("state_id", sa.Uuid()),
        sa.Column("status", record_status, server_default="ACTIVE", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["state_id"], ["states.id"], name="fk_counselling_authorities_state_id_states"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_counselling_authorities"),
        sa.UniqueConstraint("code", name="uq_counselling_authorities_code"),
    )
    op.create_index("ix_counselling_authorities_state_id", "counselling_authorities", ["state_id"])

    op.create_table(
        "catalog_releases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(64), nullable=False),
        sa.Column("academic_year", sa.SmallInteger(), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("status", release_status, server_default="DRAFT", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "academic_year >= 2000 AND academic_year <= 2100",
            name="ck_catalog_releases_academic_year_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_releases"),
        sa.UniqueConstraint(
            "domain", "academic_year", "version", name="uq_catalog_releases_domain"
        ),
    )
    op.create_index(
        "uq_catalog_releases_published_scope",
        "catalog_releases",
        ["domain", "academic_year"],
        unique=True,
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )

    op.create_table(
        "admission_cycles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("authority_id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("academic_year", sa.SmallInteger(), nullable=False),
        sa.Column("scope_state_id", sa.Uuid()),
        sa.Column("catalog_release_id", sa.Uuid()),
        sa.Column("status", admission_cycle_status, server_default="DRAFT", nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "academic_year >= 2000 AND academic_year <= 2100",
            name="ck_admission_cycles_academic_year_range",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name="ck_admission_cycles_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["authority_id"],
            ["counselling_authorities.id"],
            name="fk_admission_cycles_authority_id_counselling_authorities",
        ),
        sa.ForeignKeyConstraint(
            ["exam_id"], ["exams.id"], name="fk_admission_cycles_exam_id_exams"
        ),
        sa.ForeignKeyConstraint(
            ["scope_state_id"], ["states.id"], name="fk_admission_cycles_scope_state_id_states"
        ),
        sa.ForeignKeyConstraint(
            ["catalog_release_id"],
            ["catalog_releases.id"],
            name="fk_admission_cycles_catalog_release_id_catalog_releases",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_admission_cycles"),
        sa.UniqueConstraint(
            "authority_id",
            "exam_id",
            "academic_year",
            "scope_state_id",
            name="uq_admission_cycles_authority_id",
        ),
    )
    for column in ("authority_id", "exam_id", "scope_state_id", "catalog_release_id"):
        op.create_index(f"ix_admission_cycles_{column}", "admission_cycles", [column])

    op.create_table(
        "data_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("authority_name", sa.String(255), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("source_type", data_source_type, nullable=False),
        sa.Column("trust_tier", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column(
            "retrieval_policy", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "trust_tier >= 1 AND trust_tier <= 5", name="ck_data_sources_trust_tier_range"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_data_sources"),
        sa.UniqueConstraint("canonical_url", name="uq_data_sources_canonical_url"),
    )

    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_uri", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("publication_date", sa.Date()),
        sa.Column("academic_year", sa.SmallInteger()),
        sa.Column("media_type", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "academic_year IS NULL OR (academic_year >= 2000 AND academic_year <= 2100)",
            name="ck_source_documents_academic_year_range",
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_sources.id"],
            name="fk_source_documents_data_source_id_data_sources",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_documents"),
        sa.UniqueConstraint(
            "data_source_id", "canonical_uri", name="uq_source_documents_data_source_id"
        ),
    )
    op.create_index("ix_source_documents_data_source_id", "source_documents", ["data_source_id"])

    op.create_table(
        "source_document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("storage_uri", sa.String(2048), nullable=False),
        sa.Column("http_metadata", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("parser_version", sa.String(64)),
        sa.Column("supersedes_id", sa.Uuid()),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="ck_source_document_versions_sha256_length"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["source_documents.id"],
            name="fk_source_document_versions_document_id_source_documents",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["source_document_versions.id"],
            name="fk_source_version_supersedes",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_document_versions"),
        sa.UniqueConstraint(
            "document_id", "content_hash", name="uq_source_document_versions_document_id"
        ),
        sa.UniqueConstraint("storage_uri", name="uq_source_document_versions_storage_uri"),
    )
    op.create_index(
        "ix_source_document_versions_document_id", "source_document_versions", ["document_id"]
    )
    op.create_index(
        "ix_source_document_versions_supersedes_id", "source_document_versions", ["supersedes_id"]
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("trigger", sa.String(64), nullable=False),
        sa.Column("connector_version", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(64)),
        sa.Column("status", ingestion_run_status, server_default="RECEIVED", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("metrics", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_ingestion_runs_completion_order",
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["data_sources.id"],
            name="fk_ingestion_runs_data_source_id_data_sources",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_runs"),
        sa.UniqueConstraint("idempotency_key", name="uq_ingestion_runs_idempotency_key"),
    )
    op.create_index("ix_ingestion_runs_data_source_id", "ingestion_runs", ["data_source_id"])
    op.create_index(
        "ix_ingestion_runs_source_started", "ingestion_runs", ["data_source_id", "started_at"]
    )

    op.create_table(
        "release_source_versions",
        sa.Column("catalog_release_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_version_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["catalog_release_id"],
            ["catalog_releases.id"],
            name="fk_release_source_versions_catalog_release_id_catalog_releases",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["source_document_versions.id"],
            name="fk_release_source_document_version",
        ),
        sa.PrimaryKeyConstraint(
            "catalog_release_id", "source_document_version_id", name="pk_release_source_versions"
        ),
    )


def downgrade() -> None:
    tables = [
        "release_source_versions",
        "ingestion_runs",
        "source_document_versions",
        "source_documents",
        "data_sources",
        "admission_cycles",
        "catalog_releases",
        "counselling_authorities",
        "programs",
        "campuses",
        "institutions",
        "branches",
        "courses",
        "institution_types",
        "categories",
        "states",
        "boards",
        "exams",
    ]
    for table in tables:
        op.drop_table(table)

    bind = op.get_bind()
    ingestion_run_status.drop(bind, checkfirst=True)
    data_source_type.drop(bind, checkfirst=True)
    release_status.drop(bind, checkfirst=True)
    admission_cycle_status.drop(bind, checkfirst=True)
    record_status.drop(bind, checkfirst=True)
