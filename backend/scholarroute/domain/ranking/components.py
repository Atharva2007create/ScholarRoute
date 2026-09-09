from __future__ import annotations

from datetime import date
from decimal import Decimal
from statistics import median

from scholarroute.domain.ranking.models import (
    CollegeCandidate,
    CollegePreferences,
    ComponentScore,
    EvidenceConfidence,
    RankingReason,
    ScholarshipCandidate,
    ScholarshipPreferences,
)

NEUTRAL = Decimal("0.5")


def _score(
    name: str, value: Decimal, available: bool, *reasons: RankingReason, **details: object
) -> ComponentScore:
    return ComponentScore(
        name, max(Decimal(0), min(Decimal(1), value)), available, reasons, details
    )


def branch_score(candidate: CollegeCandidate, preferences: CollegePreferences) -> ComponentScore:
    if not preferences.preferred_branch_codes and not preferences.alternate_branch_codes:
        return _score("branch", NEUTRAL, False, RankingReason.OPTIONAL_PREFERENCE_NOT_SET)
    if candidate.branch_code in preferences.preferred_branch_codes:
        return _score("branch", Decimal(1), True, RankingReason.EXACT_BRANCH_MATCH)
    if candidate.branch_code in preferences.alternate_branch_codes:
        return _score("branch", Decimal("0.7"), True, RankingReason.ALTERNATE_BRANCH)
    return _score("branch", Decimal(0), True)


def budget_score(candidate: CollegeCandidate, preferences: CollegePreferences) -> ComponentScore:
    budget = preferences.maximum_annual_budget
    if budget is None:
        return _score("budget", NEUTRAL, False, RankingReason.OPTIONAL_PREFERENCE_NOT_SET)
    if candidate.annual_fee is None:
        return _score("budget", NEUTRAL, False, RankingReason.FEE_DATA_MISSING)
    ratio = candidate.annual_fee / budget if budget else Decimal(2)
    if ratio <= Decimal("0.8"):
        value = Decimal(1)
    elif ratio <= 1:
        value = Decimal(1) - (ratio - Decimal("0.8")) * Decimal("1.5")
    else:
        value = max(Decimal(0), Decimal("0.7") - (ratio - 1))
    reason = RankingReason.WITHIN_BUDGET if ratio <= 1 else RankingReason.ABOVE_PREFERRED_BUDGET
    return _score("budget", value, True, reason, annual_fee=candidate.annual_fee)


def location_score(candidate: CollegeCandidate, preferences: CollegePreferences) -> ComponentScore:
    if not preferences.preferred_state_codes and not preferences.acceptable_state_codes:
        return _score("location", NEUTRAL, False, RankingReason.OPTIONAL_PREFERENCE_NOT_SET)
    if candidate.state_code in preferences.preferred_state_codes:
        return _score("location", Decimal(1), True, RankingReason.PREFERRED_STATE)
    if candidate.state_code in preferences.acceptable_state_codes:
        return _score("location", Decimal("0.7"), True)
    return _score("location", Decimal(0), True)


def institution_score(
    candidate: CollegeCandidate, preferences: CollegePreferences
) -> ComponentScore:
    if not preferences.preferred_institution_type_codes:
        return _score("institution", NEUTRAL, False, RankingReason.OPTIONAL_PREFERENCE_NOT_SET)
    matched = candidate.institution_type_code in preferences.preferred_institution_type_codes
    return _score(
        "institution",
        Decimal(1 if matched else 0),
        True,
        *((RankingReason.PREFERRED_INSTITUTION_TYPE,) if matched else ()),
    )


def quality_score(candidate: CollegeCandidate) -> ComponentScore:
    if candidate.quality_signal is None:
        return _score("quality", NEUTRAL, False)
    return _score("quality", candidate.quality_signal, True, RankingReason.QUALITY_SIGNAL_AVAILABLE)


def historical_score(
    candidate: CollegeCandidate,
    *,
    student_rank: int | None,
    evaluation_year: int,
    category_code: str | None,
    quota_code: str | None,
    gender_pool_code: str | None,
) -> tuple[ComponentScore, EvidenceConfidence]:
    comparable = tuple(
        item
        for item in candidate.cutoffs
        if category_code is not None
        and quota_code is not None
        and gender_pool_code is not None
        and item.category_code == category_code
        and item.quota_code == quota_code
        and item.gender_pool_code == gender_pool_code
    )
    if student_rank is None or not comparable:
        return (
            _score("historical", NEUTRAL, False, RankingReason.LIMITED_CUTOFF_HISTORY),
            EvidenceConfidence.INSUFFICIENT,
        )
    observations = sorted(comparable, key=lambda item: (item.academic_year, item.round_sequence))
    weights = [
        Decimal(1) / Decimal(1 + max(0, evaluation_year - item.academic_year))
        for item in observations
    ]
    margins = [
        Decimal(item.closing_rank - student_rank) / Decimal(item.closing_rank)
        for item in observations
    ]
    weighted_margin = sum(
        (margin * weight for margin, weight in zip(margins, weights, strict=True)),
        Decimal(0),
    ) / sum(weights, Decimal(0))
    value = (max(Decimal(-1), min(Decimal(1), weighted_margin)) + 1) / 2
    closing = [item.closing_rank for item in observations]
    volatility = (
        Decimal(max(closing) - min(closing)) / Decimal(str(median(closing)))
        if len(closing) > 1
        else Decimal(0)
    )
    freshest_age = max(0, evaluation_year - max(item.academic_year for item in observations))
    if (
        len({item.academic_year for item in observations}) >= 3
        and volatility <= Decimal("0.25")
        and freshest_age <= 1
    ):
        confidence = EvidenceConfidence.HIGH
    elif (
        len({item.academic_year for item in observations}) >= 2
        and volatility <= Decimal("0.5")
        and freshest_age <= 2
    ):
        confidence = EvidenceConfidence.MEDIUM
    else:
        confidence = EvidenceConfidence.LOW
    reason = (
        RankingReason.STRONG_HISTORICAL_RANK_FIT
        if value >= Decimal("0.67")
        else RankingReason.HISTORICALLY_COMPETITIVE
        if value >= Decimal("0.45")
        else RankingReason.HISTORICALLY_AMBITIOUS
    )
    return _score(
        "historical",
        value,
        True,
        reason,
        observations=len(observations),
        volatility=str(volatility),
    ), confidence


def scholarship_scores(
    candidate: ScholarshipCandidate,
    preferences: ScholarshipPreferences,
    *,
    evaluation_date: date,
    maximum_benefit: Decimal | None,
) -> tuple[ComponentScore, ...] | None:
    if candidate.deadline is not None and candidate.deadline < evaluation_date:
        return None
    if candidate.benefit_amount is None or maximum_benefit is None or maximum_benefit == 0:
        benefit = _score("benefit", NEUTRAL, False, RankingReason.BENEFIT_DATA_MISSING)
    else:
        value = candidate.benefit_amount / maximum_benefit
        if (
            preferences.preferred_benefit_types
            and candidate.benefit_type not in preferences.preferred_benefit_types
        ):
            value *= Decimal("0.5")
        benefit = _score(
            "benefit",
            value,
            True,
            *((RankingReason.HIGH_SCHOLARSHIP_BENEFIT,) if value >= Decimal("0.75") else ()),
        )
    if preferences.target_program_id is None:
        course = _score("course", NEUTRAL, False, RankingReason.OPTIONAL_PREFERENCE_NOT_SET)
    else:
        course_match = (
            not candidate.eligible_program_ids
            or preferences.target_program_id in candidate.eligible_program_ids
        )
        course = _score(
            "course",
            Decimal(1 if course_match else 0),
            True,
            *((RankingReason.COURSE_RELEVANT,) if course_match else ()),
        )
    if preferences.institution_type_code is None:
        institution = _score(
            "institution", NEUTRAL, False, RankingReason.OPTIONAL_PREFERENCE_NOT_SET
        )
    else:
        institution_match = (
            not candidate.eligible_institution_types
            or preferences.institution_type_code in candidate.eligible_institution_types
        )
        institution = _score(
            "institution",
            Decimal(1 if institution_match else 0),
            True,
            *((RankingReason.INSTITUTION_COMPATIBLE,) if institution_match else ()),
        )
    if not preferences.preferred_state_codes:
        state = _score("state", NEUTRAL, False, RankingReason.OPTIONAL_PREFERENCE_NOT_SET)
    else:
        state_match = not candidate.eligible_state_codes or bool(
            candidate.eligible_state_codes & preferences.preferred_state_codes
        )
        state = _score(
            "state",
            Decimal(1 if state_match else 0),
            True,
            *((RankingReason.STATE_RELEVANT,) if state_match else ()),
        )
    if (
        candidate.application_start_date is not None
        and candidate.application_start_date > evaluation_date
    ):
        deadline = _score("deadline", NEUTRAL, True, RankingReason.APPLICATION_UPCOMING)
    elif candidate.deadline is None:
        deadline = _score("deadline", NEUTRAL, False)
    else:
        days = (candidate.deadline - evaluation_date).days
        value = Decimal(1) if days <= 30 else Decimal("0.8") if days <= 90 else Decimal("0.6")
        deadline = _score(
            "deadline",
            value,
            True,
            *((RankingReason.APPLICATION_DEADLINE_SOON,) if days <= 30 else ()),
            days_remaining=days,
        )
    return benefit, course, institution, state, deadline
