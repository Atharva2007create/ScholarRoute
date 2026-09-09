from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from scholarroute.domain.eligibility.models import EligibilityStatus
from scholarroute.domain.ranking.engine import rank_colleges, rank_scholarships
from scholarroute.domain.ranking.models import (
    CollegeCandidate,
    CollegePreferences,
    EvidenceConfidence,
    HistoricalCutoff,
    RankingDomain,
    RankingEvidence,
    RankingProfile,
    RecommendationTier,
    ScholarshipCandidate,
    ScholarshipPreferences,
)

NOW = datetime(2026, 9, 9, tzinfo=UTC)
EVIDENCE = RankingEvidence(uuid4(), "row:1", "https://official.example/source", 2025)


def college_profile(version: str = "1") -> RankingProfile:
    return RankingProfile(
        profile_id="BALANCED",
        version=version,
        domain=RankingDomain.COLLEGE,
        weights={
            "branch": Decimal("0.30"),
            "historical": Decimal("0.30"),
            "budget": Decimal("0.15"),
            "location": Decimal("0.10"),
            "institution": Decimal("0.10"),
            "quality": Decimal("0.05"),
        },
    )


def scholarship_profile() -> RankingProfile:
    return RankingProfile(
        profile_id="BALANCED",
        version="1",
        domain=RankingDomain.SCHOLARSHIP,
        weights={
            "benefit": Decimal("0.30"),
            "course": Decimal("0.25"),
            "institution": Decimal("0.15"),
            "state": Decimal("0.15"),
            "deadline": Decimal("0.15"),
        },
    )


def cutoff(year: int, closing: int, category: str = "OPEN") -> HistoricalCutoff:
    return HistoricalCutoff(year, closing, 1, category, "AI", "NEUTRAL", EVIDENCE)


def college(
    code: str,
    *,
    branch: str = "CSE",
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
    fee: Decimal | None = Decimal("100000"),
    state: str = "DL",
    cutoffs: tuple[HistoricalCutoff, ...] = (),
) -> CollegeCandidate:
    return CollegeCandidate(
        uuid4(),
        uuid4(),
        uuid4(),
        status,
        code,
        branch,
        state,
        "IIT",
        fee,
        None,
        cutoffs,
        ("https://official.example/admissions",),
        (EVIDENCE,),
    )


def rank(
    items: tuple[CollegeCandidate, ...],
    preferences: CollegePreferences,
    student_rank: int | None = None,
):
    return rank_colleges(
        candidates=items,
        preferences=preferences,
        profile=college_profile(),
        student_rank=student_rank,
        evaluation_year=2026,
        category_code="OPEN",
        quota_code="AI",
        gender_pool_code="NEUTRAL",
        evaluated_at=NOW,
    )


def test_exact_branch_and_better_historical_fit_improve_rank() -> None:
    preferred = college("A", branch="CSE", cutoffs=(cutoff(2025, 2000), cutoff(2024, 1900)))
    alternate = college("B", branch="ME", cutoffs=(cutoff(2025, 1000), cutoff(2024, 900)))
    result = rank(
        (alternate, preferred),
        CollegePreferences(preferred_branch_codes={"CSE"}, alternate_branch_codes={"ME"}),
        800,
    )
    assert result.ranked[0].subject_id == preferred.program_id
    assert result.ranked[0].components[0].score == 1


def test_historical_cutoff_is_signal_not_gate_and_wrong_pool_is_ignored() -> None:
    candidate = college("A", cutoffs=(cutoff(2025, 500), cutoff(2024, 600), cutoff(2023, 550)))
    result = rank((candidate,), CollegePreferences(), student_rank=50_000)
    assert result.ranked
    assert result.ranked[0].tier is RecommendationTier.REACH
    wrong_pool = college("B", cutoffs=(cutoff(2025, 100_000, "OBC_NCL"),))
    ignored = rank((wrong_pool,), CollegePreferences(), student_rank=100)
    assert ignored.ranked[0].confidence is EvidenceConfidence.INSUFFICIENT


def test_budget_location_and_missing_data_have_explicit_neutral_behavior() -> None:
    within = college("A", fee=Decimal("80000"), state="MH")
    above = college("B", fee=Decimal("180000"), state="KA")
    missing = college("C", fee=None, state="DL")
    preferences = CollegePreferences(
        maximum_annual_budget=Decimal("100000"), preferred_state_codes={"MH"}
    )
    result = rank((above, missing, within), preferences)
    assert result.ranked[0].subject_id == within.program_id
    missing_budget = next(
        item.components[2] for item in result.ranked if item.subject_id == missing.program_id
    )
    assert missing_budget.score == Decimal("0.5")
    assert not missing_budget.evidence_available
    neutral = rank((within,), CollegePreferences())
    assert neutral.ranked[0].components[3].score == Decimal("0.5")


def test_multi_year_history_confidence_reflects_count_and_volatility() -> None:
    stable = college("A", cutoffs=(cutoff(2025, 2000), cutoff(2024, 2100), cutoff(2023, 1950)))
    volatile = college("B", cutoffs=(cutoff(2025, 500), cutoff(2024, 5000), cutoff(2023, 700)))
    result = rank((stable, volatile), CollegePreferences(), 1000)
    confidence = {item.subject_id: item.confidence for item in result.ranked}
    assert confidence[stable.program_id] is EvidenceConfidence.HIGH
    assert confidence[volatile.program_id] is EvidenceConfidence.LOW


def test_eligibility_gate_and_needs_information_partition() -> None:
    eligible = college("A")
    failed = college("B", status=EligibilityStatus.INELIGIBLE)
    missing = college("C", status=EligibilityStatus.NEEDS_INFORMATION)
    result = rank((failed, missing, eligible), CollegePreferences())
    assert tuple(item.subject_id for item in result.ranked) == (eligible.program_id,)
    assert result.excluded_ineligible_ids == (failed.program_id,)
    assert result.needs_information_ids == (missing.program_id,)


def test_ties_and_repeated_runs_are_stable() -> None:
    first = college("A")
    second = college("B")
    left = rank((second, first), CollegePreferences())
    right = rank((second, first), CollegePreferences())
    assert [item.subject_id for item in left.ranked] == [first.program_id, second.program_id]
    assert left == right


def test_ranking_profile_validation_and_version_hashing() -> None:
    with pytest.raises(ValidationError):
        RankingProfile(
            profile_id="BAD",
            version="1",
            domain=RankingDomain.COLLEGE,
            weights={"branch": Decimal("0.9")},
        )
    with pytest.raises(ValidationError):
        RankingProfile(
            profile_id="BAD",
            version="1",
            domain=RankingDomain.COLLEGE,
            weights={"opaque": Decimal("1")},
        )
    assert college_profile("1").snapshot_hash() != college_profile("2").snapshot_hash()


def scholarship(
    code: str,
    *,
    amount: Decimal | None,
    programs: frozenset[UUID] = frozenset(),
    deadline: date | None = date(2026, 9, 20),
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
) -> ScholarshipCandidate:
    return ScholarshipCandidate(
        uuid4(),
        uuid4(),
        status,
        code,
        amount,
        "GRANT",
        programs,
        frozenset(),
        frozenset(),
        date(2026, 6, 1),
        deadline,
        ("https://official.example/apply",),
        (EVIDENCE,),
    )


def test_scholarship_relevance_benefit_deadline_links_and_gate() -> None:
    target = uuid4()
    relevant = scholarship("A", amount=Decimal("50000"), programs=frozenset({target}))
    irrelevant = scholarship("B", amount=Decimal("100000"), programs=frozenset({uuid4()}))
    expired = scholarship("C", amount=Decimal("200000"), deadline=date(2026, 1, 1))
    failed = scholarship("D", amount=Decimal("300000"), status=EligibilityStatus.INELIGIBLE)
    result = rank_scholarships(
        candidates=(irrelevant, expired, failed, relevant),
        preferences=ScholarshipPreferences(target_program_id=target),
        profile=scholarship_profile(),
        evaluation_date=NOW.date(),
        evaluated_at=NOW,
    )
    assert result.ranked[0].subject_id == relevant.scholarship_id
    assert expired.scholarship_id not in {item.subject_id for item in result.ranked}
    assert expired.scholarship_id in result.excluded_inactive_ids
    assert failed.scholarship_id in result.excluded_ineligible_ids
    assert result.ranked[0].official_links == ("https://official.example/apply",)


def test_missing_scholarship_benefit_is_neutral_not_zero() -> None:
    candidate = scholarship("A", amount=None)
    result = rank_scholarships(
        candidates=(candidate,),
        preferences=ScholarshipPreferences(),
        profile=scholarship_profile(),
        evaluation_date=NOW.date(),
        evaluated_at=NOW,
    )
    assert result.ranked[0].components[0].score == Decimal("0.5")
    assert not result.ranked[0].components[0].evidence_available
    assert all(component.score == Decimal("0.5") for component in result.ranked[0].components[:4])
