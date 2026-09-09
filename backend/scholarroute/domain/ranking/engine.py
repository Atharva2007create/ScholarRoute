from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from scholarroute.domain.eligibility.models import EligibilityStatus
from scholarroute.domain.ranking.components import (
    branch_score,
    budget_score,
    historical_score,
    institution_score,
    location_score,
    quality_score,
    scholarship_scores,
)
from scholarroute.domain.ranking.models import (
    CollegeCandidate,
    CollegePreferences,
    ComponentScore,
    EvidenceConfidence,
    RankedResult,
    RankingDomain,
    RankingOutcome,
    RankingProfile,
    RecommendationTier,
    ScholarshipCandidate,
    ScholarshipPreferences,
    preference_hash,
)


def _total(components: tuple[ComponentScore, ...], profile: RankingProfile) -> Decimal:
    scores = {component.name: component.score for component in components}
    return sum((weight * scores[name] for name, weight in profile.weights.items()), Decimal(0))


def _tier(score: Decimal, historical: ComponentScore | None = None) -> RecommendationTier:
    if historical is not None:
        if not historical.evidence_available:
            return RecommendationTier.INSUFFICIENT_DATA
        return (
            RecommendationTier.SAFER
            if historical.score >= Decimal("0.67")
            else RecommendationTier.TARGET
            if historical.score >= Decimal("0.45")
            else RecommendationTier.REACH
        )
    return (
        RecommendationTier.STRONG_FIT
        if score >= Decimal("0.75")
        else RecommendationTier.GOOD_FIT
        if score >= Decimal("0.5")
        else RecommendationTier.POSSIBLE_FIT
    )


def _partition(
    candidates: tuple[CollegeCandidate | ScholarshipCandidate, ...],
) -> tuple[list[CollegeCandidate | ScholarshipCandidate], tuple[UUID, ...], tuple[UUID, ...]]:
    eligible = [
        item for item in candidates if item.eligibility_status is EligibilityStatus.ELIGIBLE
    ]
    missing = tuple(
        item.program_id if isinstance(item, CollegeCandidate) else item.scholarship_id
        for item in candidates
        if item.eligibility_status is EligibilityStatus.NEEDS_INFORMATION
    )
    excluded = tuple(
        item.program_id if isinstance(item, CollegeCandidate) else item.scholarship_id
        for item in candidates
        if item.eligibility_status is EligibilityStatus.INELIGIBLE
    )
    return eligible, missing, excluded


def rank_colleges(
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
) -> RankingOutcome:
    if profile.domain is not RankingDomain.COLLEGE:
        raise ValueError("college ranking requires a COLLEGE ranking profile")
    eligible, missing, excluded = _partition(candidates)
    scored: list[
        tuple[CollegeCandidate, tuple[ComponentScore, ...], Decimal, EvidenceConfidence]
    ] = []
    for item in eligible:
        assert isinstance(item, CollegeCandidate)
        historical, confidence = historical_score(
            item,
            student_rank=student_rank,
            evaluation_year=evaluation_year,
            category_code=category_code,
            quota_code=quota_code,
            gender_pool_code=gender_pool_code,
        )
        components = (
            branch_score(item, preferences),
            historical,
            budget_score(item, preferences),
            location_score(item, preferences),
            institution_score(item, preferences),
            quality_score(item),
        )
        scored.append((item, components, _total(components, profile), confidence))
    scored.sort(
        key=lambda row: (
            -row[2],
            -row[1][0].score,
            -row[1][1].score,
            row[0].annual_fee is None,
            row[0].annual_fee or Decimal(0),
            row[0].canonical_code,
            str(row[0].program_id),
        )
    )
    ranked = tuple(
        RankedResult(
            item.program_id,
            item.eligibility_evaluation_id,
            index,
            total,
            _tier(total, components[1]),
            confidence,
            components,
            tuple(
                dict.fromkeys(reason for component in components for reason in component.reasons)
            ),
            f"Ranked #{index} by deterministic college fit using profile {profile.version}.",
            item.official_links,
            item.evidence + tuple(cutoff.evidence for cutoff in item.cutoffs),
            profile.version,
        )
        for index, (item, components, total, confidence) in enumerate(scored, 1)
    )
    return RankingOutcome(
        RankingDomain.COLLEGE,
        profile.snapshot_hash(),
        preference_hash(preferences),
        evaluated_at,
        ranked,
        missing,
        excluded,
        (),
    )


def rank_scholarships(
    *,
    candidates: tuple[ScholarshipCandidate, ...],
    preferences: ScholarshipPreferences,
    profile: RankingProfile,
    evaluation_date: date,
    evaluated_at: datetime,
) -> RankingOutcome:
    if profile.domain is not RankingDomain.SCHOLARSHIP:
        raise ValueError("scholarship ranking requires a SCHOLARSHIP ranking profile")
    eligible, missing, excluded = _partition(candidates)
    amounts = [
        item.benefit_amount
        for item in eligible
        if isinstance(item, ScholarshipCandidate) and item.benefit_amount is not None
    ]
    maximum = max(amounts) if amounts else None
    inactive = tuple(
        item.scholarship_id
        for item in eligible
        if isinstance(item, ScholarshipCandidate)
        and item.deadline is not None
        and item.deadline < evaluation_date
    )
    scored: list[tuple[ScholarshipCandidate, tuple[ComponentScore, ...], Decimal]] = []
    for item in eligible:
        assert isinstance(item, ScholarshipCandidate)
        components = scholarship_scores(
            item, preferences, evaluation_date=evaluation_date, maximum_benefit=maximum
        )
        if components is not None:
            scored.append((item, components, _total(components, profile)))
    scored.sort(
        key=lambda row: (
            -row[2],
            -row[1][1].score,
            -row[1][0].score,
            -row[1][4].score,
            row[0].canonical_code,
            str(row[0].scholarship_id),
        )
    )
    ranked = tuple(
        RankedResult(
            item.scholarship_id,
            item.eligibility_evaluation_id,
            index,
            total,
            _tier(total),
            EvidenceConfidence.HIGH
            if all(component.evidence_available for component in components)
            else EvidenceConfidence.MEDIUM,
            components,
            tuple(
                dict.fromkeys(reason for component in components for reason in component.reasons)
            ),
            f"Ranked #{index} by deterministic scholarship fit using profile {profile.version}.",
            item.official_links,
            item.evidence,
            profile.version,
        )
        for index, (item, components, total) in enumerate(scored, 1)
    )
    return RankingOutcome(
        RankingDomain.SCHOLARSHIP,
        profile.snapshot_hash(),
        preference_hash(preferences),
        evaluated_at,
        ranked,
        missing,
        excluded,
        inactive,
    )
