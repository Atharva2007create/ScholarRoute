from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from scholarroute.infrastructure.db.base import Base, UUIDPrimaryKeyMixin
from scholarroute.infrastructure.db.models.enums import RankingDomain


class RankingProfileRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ranking_profiles"
    __table_args__ = (UniqueConstraint("profile_key", "version", "domain"),)

    profile_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[RankingDomain] = mapped_column(
        Enum(RankingDomain, name="ranking_domain"), nullable=False
    )
    weights: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    normalization_version: Mapped[str] = mapped_column(String(64), nullable=False)
    tie_breaking_version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RankingRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ranking_runs"
    __table_args__ = (
        CheckConstraint("length(profile_hash) = 64", name="profile_hash_length"),
        CheckConstraint("length(preference_hash) = 64", name="preference_hash_length"),
        Index("ix_ranking_runs_domain_evaluated", "domain", "evaluated_at"),
    )

    domain: Mapped[RankingDomain] = mapped_column(
        Enum(RankingDomain, name="ranking_domain"), nullable=False
    )
    ranking_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_profiles.id"), nullable=False, index=True
    )
    profile_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preference_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preference_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    ranking_profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    needs_information_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    excluded_ineligible_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    excluded_inactive_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)


class RankedRecommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ranked_recommendations"
    __table_args__ = (
        UniqueConstraint("ranking_run_id", "rank_position", name="uq_ranked_run_position"),
        UniqueConstraint("ranking_run_id", "subject_id", name="uq_ranked_run_subject"),
        CheckConstraint("rank_position > 0", name="positive_position"),
        CheckConstraint("overall_score >= 0 AND overall_score <= 1", name="score_range"),
        Index("ix_ranked_recommendations_subject", "subject_id", "ranking_run_id"),
    )

    ranking_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[UUID] = mapped_column(nullable=False)
    eligibility_evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("eligibility_evaluations.id"), nullable=False, index=True
    )
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(18, 16), nullable=False)
    tier: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(64), nullable=False)
    component_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    deterministic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    official_links: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
