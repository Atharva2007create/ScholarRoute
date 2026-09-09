from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from scholarroute.domain.eligibility.models import EligibilityStatus
from scholarroute.domain.ranking.engine import rank_colleges, rank_scholarships
from scholarroute.domain.ranking.models import (
    CollegeCandidate,
    CollegePreferences,
    RankingOutcome,
    RankingProfile,
    ScholarshipCandidate,
    ScholarshipPreferences,
)
from scholarroute.infrastructure.db.models import (
    EligibilityEvaluation,
    RankedRecommendation,
    RankingProfileRecord,
    RankingRun,
)
from scholarroute.infrastructure.db.models.enums import RankingDomain as DatabaseRankingDomain


@dataclass(frozen=True)
class PersistedRanking:
    run_id: UUID
    outcome: RankingOutcome


def _json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (UUID, Decimal, date, datetime)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json(item) for item in value]
    return value


class RankingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def rank_colleges(
        self,
        *,
        candidates: tuple[CollegeCandidate, ...],
        preferences: CollegePreferences,
        profile: RankingProfile,
        student_rank: int | None,
        evaluation_year: int,
        category_code: str | None,
        quota_code: str | None,
        gender_pool_code: str | None,
        evaluated_at: datetime,
    ) -> PersistedRanking:
        verified = self._verify_candidates(candidates)
        outcome = rank_colleges(
            candidates=verified,
            preferences=preferences,
            profile=profile,
            student_rank=student_rank,
            evaluation_year=evaluation_year,
            category_code=category_code,
            quota_code=quota_code,
            gender_pool_code=gender_pool_code,
            evaluated_at=evaluated_at,
        )
        return self._persist(outcome, preferences, profile)

    def rank_scholarships(
        self,
        *,
        candidates: tuple[ScholarshipCandidate, ...],
        preferences: ScholarshipPreferences,
        profile: RankingProfile,
        evaluation_date: date,
        evaluated_at: datetime,
    ) -> PersistedRanking:
        verified = self._verify_candidates(candidates)
        outcome = rank_scholarships(
            candidates=verified,
            preferences=preferences,
            profile=profile,
            evaluation_date=evaluation_date,
            evaluated_at=evaluated_at,
        )
        return self._persist(outcome, preferences, profile)

    def _verify_candidates(self, candidates: tuple[Any, ...]) -> tuple[Any, ...]:
        evaluation_ids = {item.eligibility_evaluation_id for item in candidates}
        records = {
            item.id: item
            for item in self.session.scalars(
                select(EligibilityEvaluation).where(EligibilityEvaluation.id.in_(evaluation_ids))
            )
        }
        if set(records) != evaluation_ids:
            raise ValueError("every ranking candidate requires a stored Phase 4 evaluation")
        verified = []
        for candidate in candidates:
            record = records[candidate.eligibility_evaluation_id]
            subject_id = (
                candidate.program_id
                if isinstance(candidate, CollegeCandidate)
                else candidate.scholarship_id
            )
            if record.subject_id != subject_id:
                raise ValueError("candidate does not match its Phase 4 eligibility subject")
            verified.append(
                replace(candidate, eligibility_status=EligibilityStatus(record.status.value))
            )
        return tuple(verified)

    def _persist(
        self, outcome: RankingOutcome, preferences: BaseModel, profile: RankingProfile
    ) -> PersistedRanking:
        db_domain = DatabaseRankingDomain(profile.domain.value)
        record = self.session.scalar(
            select(RankingProfileRecord).where(
                RankingProfileRecord.profile_key == profile.profile_id,
                RankingProfileRecord.version == profile.version,
                RankingProfileRecord.domain == db_domain,
            )
        )
        snapshot = profile.model_dump(mode="json")
        if record is None:
            record = RankingProfileRecord(
                profile_key=profile.profile_id,
                version=profile.version,
                domain=db_domain,
                weights=_json(profile.weights),
                normalization_version=profile.normalization_version,
                tie_breaking_version=profile.tie_breaking_version,
            )
            self.session.add(record)
            self.session.flush()
        elif (
            _json(record.weights) != _json(profile.weights)
            or record.normalization_version != profile.normalization_version
            or record.tie_breaking_version != profile.tie_breaking_version
        ):
            raise ValueError("stored ranking profile version is immutable and differs from input")
        run = RankingRun(
            domain=db_domain,
            ranking_profile_id=record.id,
            profile_hash=outcome.profile_hash,
            preference_hash=outcome.preference_hash,
            preference_snapshot=preferences.model_dump(mode="json"),
            ranking_profile_snapshot=snapshot,
            evaluated_at=outcome.evaluated_at,
            needs_information_ids=[str(item) for item in outcome.needs_information_ids],
            excluded_ineligible_ids=[str(item) for item in outcome.excluded_ineligible_ids],
            excluded_inactive_ids=[str(item) for item in outcome.excluded_inactive_ids],
        )
        self.session.add(run)
        self.session.flush()
        for item in outcome.ranked:
            self.session.add(
                RankedRecommendation(
                    ranking_run_id=run.id,
                    subject_id=item.subject_id,
                    eligibility_evaluation_id=item.eligibility_evaluation_id,
                    rank_position=item.rank_position,
                    overall_score=item.overall_score,
                    tier=item.tier.value,
                    confidence=item.confidence.value,
                    component_scores=_json([asdict(component) for component in item.components]),
                    reason_codes=[reason.value for reason in item.reason_codes],
                    deterministic_summary=item.deterministic_summary,
                    official_links=list(item.official_links),
                    evidence=_json([asdict(evidence) for evidence in item.evidence]),
                )
            )
        self.session.flush()
        return PersistedRanking(run.id, outcome)
