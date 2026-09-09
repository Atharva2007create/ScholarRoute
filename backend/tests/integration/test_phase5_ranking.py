from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scholarroute.application.ranking.service import RankingService
from scholarroute.domain.eligibility.models import EligibilityStatus
from scholarroute.domain.ranking.models import (
    CollegeCandidate,
    CollegePreferences,
    HistoricalCutoff,
    RankingDomain,
    RankingEvidence,
    RankingProfile,
)
from scholarroute.infrastructure.db.models import (
    EligibilityEvaluation,
    EligibilityInputSnapshot,
    RankedRecommendation,
    RankingRun,
)
from scholarroute.infrastructure.db.models.enums import (
    EligibilityStatus as DatabaseEligibilityStatus,
)
from scholarroute.infrastructure.db.models.enums import (
    EligibilitySubjectType as DatabaseEligibilitySubjectType,
)
from scholarroute.infrastructure.db.session import session_scope

NOW = datetime(2026, 9, 9, tzinfo=UTC)


def _eligibility(
    session: Session,
    subject_id: UUID,
    status: DatabaseEligibilityStatus = DatabaseEligibilityStatus.ELIGIBLE,
) -> UUID:
    snapshot = EligibilityInputSnapshot(
        profile_identifier="synthetic-student",
        schema_version="1",
        evaluation_year=2026,
        input_hash="a" * 64,
        normalized_input={"evaluation_year": 2026},
    )
    session.add(snapshot)
    session.flush()
    evaluation = EligibilityEvaluation(
        snapshot_id=snapshot.id,
        subject_type=DatabaseEligibilitySubjectType.PROGRAM,
        subject_id=subject_id,
        evaluation_year=2026,
        status=status,
        rule_set_version="2026.1",
        rules_hash="b" * 64,
        evaluated_at=NOW,
        reason_codes=["PASS_MINIMUM_MARKS"],
        missing_information=[],
        human_summary="Eligible under published synthetic rules.",
    )
    session.add(evaluation)
    session.flush()
    return evaluation.id


def test_phase5_ranking_audit_snapshot_and_reproducibility(migrated_database: str) -> None:
    del migrated_database
    with session_scope() as session:
        evidence = RankingEvidence(uuid4(), "cutoff!row:1", "https://official.example/cutoff", 2025)
        candidates = []
        for code, branch, closing in (("A", "CSE", 2000), ("B", "ME", 1000)):
            program_id = uuid4()
            stored_status = (
                DatabaseEligibilityStatus.ELIGIBLE
                if code == "A"
                else DatabaseEligibilityStatus.INELIGIBLE
            )
            candidates.append(
                CollegeCandidate(
                    program_id=program_id,
                    institution_id=uuid4(),
                    eligibility_evaluation_id=_eligibility(session, program_id, stored_status),
                    eligibility_status=EligibilityStatus.ELIGIBLE,
                    canonical_code=code,
                    branch_code=branch,
                    state_code="DL",
                    institution_type_code="IIT",
                    annual_fee=Decimal("100000"),
                    quality_signal=None,
                    cutoffs=(
                        HistoricalCutoff(2025, closing, 1, "OPEN", "AI", "NEUTRAL", evidence),
                    ),
                    official_links=("https://official.example/admissions",),
                    evidence=(evidence,),
                )
            )
        profile = RankingProfile(
            profile_id="BALANCED",
            version="2026.1",
            domain=RankingDomain.COLLEGE,
            weights={
                "branch": Decimal("0.4"),
                "historical": Decimal("0.4"),
                "budget": Decimal("0.1"),
                "location": Decimal("0.05"),
                "institution": Decimal("0.05"),
                "quality": Decimal("0"),
            },
        )
        preferences = CollegePreferences(preferred_branch_codes={"CSE"})
        service = RankingService(session)
        first = service.rank_colleges(
            candidates=tuple(candidates),
            preferences=preferences,
            profile=profile,
            student_rank=800,
            evaluation_year=2026,
            category_code="OPEN",
            quota_code="AI",
            gender_pool_code="NEUTRAL",
            evaluated_at=NOW,
        )
        second = service.rank_colleges(
            candidates=tuple(candidates),
            preferences=preferences,
            profile=profile,
            student_rank=800,
            evaluation_year=2026,
            category_code="OPEN",
            quota_code="AI",
            gender_pool_code="NEUTRAL",
            evaluated_at=NOW,
        )
        assert first.run_id != second.run_id
        assert first.outcome == second.outcome
        assert first.outcome.excluded_ineligible_ids == (candidates[1].program_id,)
        assert first.outcome.ranked[0].official_links
        assert first.outcome.ranked[0].evidence[0].source_locator == "cutoff!row:1"
        assert session.scalar(select(func.count()).select_from(RankingRun)) == 2
        assert session.scalar(select(func.count()).select_from(RankedRecommendation)) == 2
