"""Add verified media assets with provenance.

Revision ID: 5c3d3fd892a1
Revises: f910e48492d8
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c3d3fd892a1"
down_revision: str | None = "f910e48492d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("asset_url", sa.String(length=2048), nullable=False),
        sa.Column("source_page_url", sa.String(length=2048), nullable=False),
        sa.Column("official_domain", sa.String(length=255), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("content_length", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("usage_note", sa.String(length=500), nullable=True),
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
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "entity_type IN ('INSTITUTION', 'SCHOLARSHIP_PROVIDER')",
            name=op.f("ck_media_assets_entity_type_supported"),
        ),
        sa.CheckConstraint(
            "media_type IN ('LOGO', 'CAMPUS_IMAGE', 'SCHEME_LOGO')",
            name=op.f("ck_media_assets_media_type_supported"),
        ),
        sa.CheckConstraint(
            "validation_status = 'VERIFIED'", name=op.f("ck_media_assets_verified_only")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "media_type",
            name=op.f("uq_media_assets_entity_type"),
        ),
    )
    op.create_index(
        "ix_media_assets_entity", "media_assets", ["entity_type", "entity_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_media_assets_entity", table_name="media_assets")
    op.drop_table("media_assets")
