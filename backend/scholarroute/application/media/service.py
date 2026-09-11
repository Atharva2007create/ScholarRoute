from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from scholarroute.infrastructure.db.models import (
    MediaAsset,
    Program,
    ScholarshipProvider,
    ScholarshipScheme,
)


def media_for_college_programs(
    session: Session, subject_ids: Iterable[UUID]
) -> dict[UUID, dict[str, Any]]:
    rows = session.execute(
        select(Program.id, MediaAsset)
        .join(
            MediaAsset,
            (MediaAsset.entity_type == "INSTITUTION")
            & (MediaAsset.entity_id == Program.institution_id),
        )
        .where(
            Program.id.in_(tuple(subject_ids)),
            MediaAsset.validation_status == "VERIFIED",
        )
    ).tuples().all()
    return _group(rows, scholarship=False)


def media_for_scholarships(
    session: Session, subject_ids: Iterable[UUID]
) -> dict[UUID, dict[str, Any]]:
    rows = session.execute(
        select(ScholarshipScheme.id, MediaAsset)
        .join(ScholarshipProvider, ScholarshipProvider.id == ScholarshipScheme.provider_id)
        .join(
            MediaAsset,
            (MediaAsset.entity_type == "SCHOLARSHIP_PROVIDER")
            & (MediaAsset.entity_id == ScholarshipProvider.id),
        )
        .where(
            ScholarshipScheme.id.in_(tuple(subject_ids)),
            MediaAsset.validation_status == "VERIFIED",
        )
    ).tuples().all()
    return _group(rows, scholarship=True)


def _group(
    rows: Iterable[tuple[UUID, MediaAsset]], *, scholarship: bool
) -> dict[UUID, dict[str, Any]]:
    grouped: dict[UUID, dict[str, Any]] = {}
    for subject_id, asset in rows:
        item = grouped.setdefault(subject_id, {})
        if scholarship:
            field = "scheme_logo_url" if asset.media_type == "SCHEME_LOGO" else "provider_logo_url"
        else:
            field = (
                "campus_image_url"
                if asset.media_type == "CAMPUS_IMAGE"
                else "institution_logo_url"
            )
        item[field] = asset.asset_url
        item["media_source_url"] = asset.source_page_url
        item["media_verified_at"] = asset.retrieved_at
    return grouped
