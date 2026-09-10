from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scholarroute.application.eligibility.repository import RuleSetNotFoundError
from scholarroute.application.eligibility.service import EligibilityService
from scholarroute.application.ranking.service import PersistedRanking, RankingService
from scholarroute.domain.eligibility.models import StudentEligibilityInput
from scholarroute.domain.ranking.models import (
    CollegeCandidate,
    CollegePreferences,
    HistoricalCutoff,
    RankingDomain,
    RankingEvidence,
    RankingProfile,
    ScholarshipCandidate,
    ScholarshipPreferences,
)
from scholarroute.infrastructure.db.models import (
    AdmissionCycle,
    AdmissionRequirement,
    Branch,
    Category,
    CounsellingRound,
    Course,
    CutoffObservation,
    FeeSchedule,
    GenderPool,
    Institution,
    InstitutionType,
    Program,
    ProgramOffering,
    QuotaType,
    ScholarshipBenefit,
    ScholarshipCycle,
    ScholarshipEligibilityRule,
    ScholarshipEligibleInstitutionType,
    ScholarshipEligibleProgram,
    ScholarshipEligibleState,
    ScholarshipProvider,
    ScholarshipScheme,
    SourceDocument,
    SourceDocumentVersion,
    State,
)
from scholarroute.infrastructure.db.models.enums import RecordStatus, ScholarshipStatus


@dataclass(frozen=True)
class DiscoveryResult:
    ranking: PersistedRanking
    details: dict[UUID, dict[str, Any]]


def _college_profile(preset: str) -> RankingProfile:
    weights = {
        "BALANCED": ("0.30", "0.30", "0.15", "0.10", "0.10", "0.05"),
        "BRANCH_FIRST": ("0.50", "0.25", "0.10", "0.05", "0.05", "0.05"),
        "BUDGET_FIRST": ("0.25", "0.20", "0.35", "0.08", "0.07", "0.05"),
        "LOCATION_FIRST": ("0.25", "0.20", "0.10", "0.30", "0.10", "0.05"),
    }[preset]
    return RankingProfile(
        profile_id=f"API_{preset}",
        version="2026.1",
        domain=RankingDomain.COLLEGE,
        weights=dict(
            zip(
                ("branch", "historical", "budget", "location", "institution", "quality"),
                map(Decimal, weights),
                strict=True,
            )
        ),
    )


def _scholarship_profile() -> RankingProfile:
    return RankingProfile(
        profile_id="API_BALANCED",
        version="2026.1",
        domain=RankingDomain.SCHOLARSHIP,
        weights={
            "benefit": Decimal("0.30"),
            "course": Decimal("0.25"),
            "institution": Decimal("0.15"),
            "state": Decimal("0.15"),
            "deadline": Decimal("0.15"),
        },
    )


class DiscoveryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def colleges(
        self,
        *,
        student: StudentEligibilityInput,
        preferences: CollegePreferences,
        preset: str,
        state_code: str | None,
        branch_code: str | None,
        institution_type_code: str | None,
    ) -> DiscoveryResult:
        query = (
            select(Program, Institution, State, InstitutionType, Branch)
            .join(Institution, Institution.id == Program.institution_id)
            .join(State, State.id == Institution.state_id)
            .join(InstitutionType, InstitutionType.id == Institution.institution_type_id)
            .outerjoin(Branch, Branch.id == Program.branch_id)
            .join(AdmissionRequirement, AdmissionRequirement.program_id == Program.id)
            .where(
                Program.status == RecordStatus.ACTIVE,
                AdmissionRequirement.academic_year == student.evaluation_year,
            )
        )
        if student.target_course_code:
            query = query.join(Course, Course.id == Program.course_id).where(
                Course.code == student.target_course_code
            )
        if state_code:
            query = query.where(State.code == state_code)
        if branch_code:
            query = query.where(Branch.code == branch_code)
        if institution_type_code:
            query = query.where(InstitutionType.code == institution_type_code)
        rows = self.session.execute(query.distinct().limit(200)).all()
        program_ids = {row[0].id for row in rows}
        fees = {
            program_id: amount
            for program_id, amount in self.session.execute(
                select(FeeSchedule.program_id, func.sum(FeeSchedule.amount))
                .where(
                    FeeSchedule.program_id.in_(program_ids),
                    FeeSchedule.academic_year == student.evaluation_year,
                )
                .group_by(FeeSchedule.program_id)
            )
            if program_id is not None
        }
        cutoff_map: dict[UUID, list[HistoricalCutoff]] = {}
        cutoff_query = (
            select(
                ProgramOffering.program_id,
                AdmissionCycle.academic_year,
                CutoffObservation.closing_rank,
                CounsellingRound.sequence,
                Category.code,
                QuotaType.code,
                GenderPool.code,
                SourceDocumentVersion.id,
                SourceDocument.canonical_uri,
                CutoffObservation.source_locator,
            )
            .join(CutoffObservation, CutoffObservation.offering_id == ProgramOffering.id)
            .join(CounsellingRound, CounsellingRound.id == CutoffObservation.round_id)
            .join(AdmissionCycle, AdmissionCycle.id == ProgramOffering.admission_cycle_id)
            .join(Category, Category.id == ProgramOffering.category_id)
            .join(QuotaType, QuotaType.id == ProgramOffering.quota_type_id)
            .join(GenderPool, GenderPool.id == ProgramOffering.gender_pool_id)
            .join(
                SourceDocumentVersion,
                SourceDocumentVersion.id == CutoffObservation.source_document_version_id,
            )
            .join(SourceDocument, SourceDocument.id == SourceDocumentVersion.document_id)
            .where(
                ProgramOffering.program_id.in_(program_ids),
                AdmissionCycle.academic_year.between(
                    student.evaluation_year - 3, student.evaluation_year
                ),
            )
        )
        for item in self.session.execute(cutoff_query):
            cutoff_map.setdefault(item[0], []).append(
                HistoricalCutoff(
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                    item[5],
                    item[6],
                    RankingEvidence(item[7], item[9], item[8], item[1]),
                )
            )
        candidates = []
        details: dict[UUID, dict[str, Any]] = {}
        eligibility = EligibilityService(self.session)
        for program, institution, state, institution_type, branch in rows:
            try:
                evaluated = eligibility.evaluate_program(profile=student, program_id=program.id)
            except RuleSetNotFoundError:
                continue
            candidates.append(
                CollegeCandidate(
                    program.id,
                    institution.id,
                    evaluated.evaluation_id,
                    evaluated.decision.status,
                    program.code,
                    branch.code if branch else None,
                    state.code,
                    institution_type.code,
                    fees.get(program.id),
                    None,
                    tuple(cutoff_map.get(program.id, ())),
                    evaluated.official_links,
                )
            )
            details[program.id] = {
                "title": program.name,
                "organization": institution.official_name,
                "state_code": state.code,
                "annual_fee": fees.get(program.id),
            }
        ranked = RankingService(self.session).rank_colleges(
            candidates=tuple(candidates),
            preferences=preferences,
            profile=_college_profile(preset),
            student_rank=student.exam_rank,
            evaluation_year=student.evaluation_year,
            category_code=student.category_code,
            quota_code=student.quota_code,
            gender_pool_code=student.gender_pool_code,
            evaluated_at=datetime.now(UTC),
        )
        return DiscoveryResult(ranked, details)

    def scholarships(
        self,
        *,
        student: StudentEligibilityInput,
        preferences: ScholarshipPreferences,
        benefit_type: str | None,
        provider_code: str | None,
    ) -> DiscoveryResult:
        query = (
            select(
                ScholarshipCycle, ScholarshipScheme, ScholarshipProvider, ScholarshipEligibilityRule
            )
            .join(ScholarshipScheme, ScholarshipScheme.id == ScholarshipCycle.scheme_id)
            .join(ScholarshipProvider, ScholarshipProvider.id == ScholarshipScheme.provider_id)
            .join(
                ScholarshipEligibilityRule,
                ScholarshipEligibilityRule.cycle_id == ScholarshipCycle.id,
            )
            .where(
                ScholarshipCycle.academic_year == student.evaluation_year,
                ScholarshipCycle.status.in_((ScholarshipStatus.OPEN, ScholarshipStatus.PUBLISHED)),
            )
        )
        if provider_code:
            query = query.where(ScholarshipProvider.code == provider_code)
        rows = self.session.execute(query.limit(200)).all()
        cycle_ids = {row[0].id for row in rows}
        benefits = {
            cycle_id: (amount, kind)
            for cycle_id, amount, kind in self.session.execute(
                select(
                    ScholarshipBenefit.cycle_id,
                    ScholarshipBenefit.amount_max,
                    ScholarshipBenefit.benefit_type,
                ).where(ScholarshipBenefit.cycle_id.in_(cycle_ids))
            )
        }
        if benefit_type:
            rows = [row for row in rows if benefits.get(row[0].id, (None, None))[1] == benefit_type]

        def association(model: Any, value: Any) -> dict[UUID, set[Any]]:
            output: dict[UUID, set[Any]] = {}
            for cycle_id, item in self.session.execute(
                select(model.cycle_id, value).where(model.cycle_id.in_(cycle_ids))
            ):
                output.setdefault(cycle_id, set()).add(item)
            return output

        programs = association(ScholarshipEligibleProgram, ScholarshipEligibleProgram.program_id)
        state_ids = association(ScholarshipEligibleState, ScholarshipEligibleState.state_id)
        type_ids = association(
            ScholarshipEligibleInstitutionType,
            ScholarshipEligibleInstitutionType.institution_type_id,
        )
        state_codes = {
            item.id: item.code
            for item in self.session.scalars(
                select(State).where(
                    State.id.in_(set().union(*state_ids.values()) if state_ids else set())
                )
            )
        }
        type_codes = {
            item.id: item.code
            for item in self.session.scalars(
                select(InstitutionType).where(
                    InstitutionType.id.in_(set().union(*type_ids.values()) if type_ids else set())
                )
            )
        }
        candidates = []
        details: dict[UUID, dict[str, Any]] = {}
        eligibility = EligibilityService(self.session)
        for cycle, scheme, provider, _ in rows:
            evaluated = eligibility.evaluate_scholarship(profile=student, cycle_id=cycle.id)
            amount, kind = benefits.get(cycle.id, (None, None))
            candidates.append(
                ScholarshipCandidate(
                    scheme.id,
                    evaluated.evaluation_id,
                    evaluated.decision.status,
                    scheme.official_code,
                    amount,
                    kind,
                    frozenset(programs.get(cycle.id, set())),
                    frozenset(type_codes[item] for item in type_ids.get(cycle.id, set())),
                    frozenset(state_codes[item] for item in state_ids.get(cycle.id, set())),
                    cycle.application_start_date,
                    cycle.deadline,
                    evaluated.official_links,
                )
            )
            details[scheme.id] = {
                "title": scheme.name,
                "organization": provider.name,
                "deadline": cycle.deadline,
                "benefit_amount": amount,
            }
        ranked = RankingService(self.session).rank_scholarships(
            candidates=tuple(candidates),
            preferences=preferences,
            profile=_scholarship_profile(),
            evaluation_date=student.evaluation_date or date(student.evaluation_year, 8, 1),
            evaluated_at=datetime.now(UTC),
        )
        return DiscoveryResult(ranked, details)
