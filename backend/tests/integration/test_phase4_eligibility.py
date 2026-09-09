from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from scholarroute.application.eligibility.service import EligibilityService
from scholarroute.application.ingestion.contracts import SourceContext
from scholarroute.application.ingestion.importers import JoSAAImporter, MCCImporter, NSPImporter
from scholarroute.application.ingestion.service import run_ingestion
from scholarroute.domain.eligibility.models import EligibilityStatus, StudentEligibilityInput
from scholarroute.infrastructure.db.models import (
    AdmissionRequirement,
    EligibilityEvaluation,
    EligibilityInputSnapshot,
    EligibilityRuleResult,
    Exam,
    Program,
    ScholarshipCycle,
    ScholarshipScheme,
    SourceDocument,
    SourceDocumentVersion,
)
from scholarroute.infrastructure.db.session import session_scope

FIXTURES = Path(__file__).parents[1] / "fixtures"
EVALUATED_AT = datetime(2025, 8, 1, tzinfo=UTC)


def test_phase4_program_and_scholarship_decisions_are_auditable(
    migrated_database: str,
) -> None:
    del migrated_database
    with session_scope() as session:
        run_ingestion(
            session,
            importer=JoSAAImporter(),
            path=FIXTURES / "josaa_2025_test.csv",
            context=SourceContext(
                authority_code="JOSAA",
                authority_name="Joint Seat Allocation Authority",
                official_domain="josaa.nic.in",
                source_url="https://josaa.nic.in/test/2025.csv",
                title="JoSAA eligibility fixture",
                academic_year=2025,
            ),
        )
        run_ingestion(
            session,
            importer=NSPImporter(),
            path=FIXTURES / "scholarships_2025_test.xlsx",
            context=SourceContext(
                authority_code="NSP",
                authority_name="National Scholarship Portal",
                official_domain="scholarships.gov.in",
                source_url="https://scholarships.gov.in/test/2025.xlsx",
                title="NSP eligibility fixture",
                academic_year=2025,
            ),
        )
        run_ingestion(
            session,
            importer=MCCImporter(),
            path=FIXTURES / "neet_2025_test.json",
            context=SourceContext(
                authority_code="MCC",
                authority_name="Medical Counselling Committee",
                official_domain="mcc.nic.in",
                source_url="https://mcc.nic.in/test/2025.json",
                title="MCC eligibility fixture",
                academic_year=2025,
            ),
        )
        program = session.scalar(select(Program).where(Program.code == "TEST-IIT-DL-CSE"))
        exam = session.scalar(select(Exam).where(Exam.code == "JEE_MAIN"))
        source_version = session.scalar(
            select(SourceDocumentVersion)
            .join(SourceDocument)
            .where(SourceDocument.canonical_uri == "https://josaa.nic.in/test/2025.csv")
        )
        assert program is not None and exam is not None and source_version is not None
        session.add(
            AdmissionRequirement(
                code="JEE-2025-BASE",
                academic_year=2025,
                exam_id=exam.id,
                program_id=program.id,
                minimum_marks=Decimal("60"),
                maximum_exam_rank=2000,
                rule_version="2025.1",
                summary="Published program eligibility fixture",
                source_locator="eligibility!page:4",
                source_document_version_id=source_version.id,
            )
        )
        session.flush()

        service = EligibilityService(session)
        profile = StudentEligibilityInput(
            profile_id="student-1",
            evaluation_year=2025,
            exam_code="jee main",
            exam_rank=1000,
            class12_percentage=Decimal("75"),
        )
        first = service.evaluate_program(
            profile=profile,
            program_id=program.id,
            evaluated_at=EVALUATED_AT,
        )
        second = service.evaluate_program(
            profile=profile,
            program_id=program.id,
            evaluated_at=EVALUATED_AT,
        )
        assert first.decision.status is EligibilityStatus.ELIGIBLE
        assert first.decision.student_snapshot_hash == second.decision.student_snapshot_hash
        assert first.evaluation_id != second.evaluation_id
        assert first.official_links
        assert all(link.startswith("https://") for link in first.official_links)

        neet_program = session.scalar(select(Program).where(Program.code == "TEST-MED-RJ-MBBS"))
        neet_exam = session.scalar(select(Exam).where(Exam.code == "NEET_UG"))
        neet_source = session.scalar(
            select(SourceDocumentVersion)
            .join(SourceDocument)
            .where(SourceDocument.canonical_uri == "https://mcc.nic.in/test/2025.json")
        )
        assert neet_program is not None and neet_exam is not None and neet_source is not None
        session.add(
            AdmissionRequirement(
                code="NEET-2025-BASE",
                academic_year=2025,
                exam_id=neet_exam.id,
                program_id=neet_program.id,
                minimum_exam_score=Decimal("50"),
                rule_version="2025.1",
                summary="Published NEET eligibility fixture",
                source_locator="neet-rules!page:7",
                source_document_version_id=neet_source.id,
            )
        )
        session.flush()
        neet_result = service.evaluate_program(
            profile=StudentEligibilityInput(
                evaluation_year=2025,
                exam_code="NEET_UG",
                exam_score=Decimal("60"),
                exam_rank=50_000,
            ),
            program_id=neet_program.id,
            evaluated_at=EVALUATED_AT,
        )
        assert neet_result.decision.status is EligibilityStatus.ELIGIBLE

        scheme = session.scalar(
            select(ScholarshipScheme).where(ScholarshipScheme.official_code == "NSP-TEST-MERIT")
        )
        assert scheme is not None
        cycle = session.scalar(
            select(ScholarshipCycle).where(ScholarshipCycle.scheme_id == scheme.id)
        )
        assert cycle is not None
        scholarship = service.evaluate_scholarship(
            profile=StudentEligibilityInput(
                profile_id="student-1",
                evaluation_year=2025,
                family_income=Decimal("500000"),
                class12_percentage=Decimal("75"),
            ),
            cycle_id=cycle.id,
            evaluated_at=EVALUATED_AT,
        )
        assert scholarship.decision.status is EligibilityStatus.ELIGIBLE
        assert len(scholarship.official_links) == 3

        assert session.scalar(select(func.count()).select_from(EligibilityInputSnapshot)) == 4
        assert session.scalar(select(func.count()).select_from(EligibilityEvaluation)) == 4
        assert session.scalar(select(func.count()).select_from(EligibilityRuleResult)) >= 8
        evidence_rows = list(
            session.scalars(
                select(EligibilityRuleResult).where(
                    EligibilityRuleResult.evaluation_id == first.evaluation_id
                )
            )
        )
        assert all(row.source_document_version_id == source_version.id for row in evidence_rows)
        assert all(row.source_locator == "eligibility!page:4" for row in evidence_rows)


def test_phase4_missing_scholarship_data_is_not_treated_as_eligible(
    migrated_database: str,
) -> None:
    del migrated_database
    with session_scope() as session:
        run_ingestion(
            session,
            importer=NSPImporter(),
            path=FIXTURES / "scholarships_2025_test.xlsx",
            context=SourceContext(
                authority_code="NSP",
                authority_name="National Scholarship Portal",
                official_domain="scholarships.gov.in",
                source_url="https://scholarships.gov.in/test/2025.xlsx",
                title="NSP missing-data fixture",
                academic_year=2025,
            ),
        )
        scheme = session.scalar(
            select(ScholarshipScheme).where(ScholarshipScheme.official_code == "NSP-TEST-MERIT")
        )
        assert scheme is not None
        cycle = session.scalar(
            select(ScholarshipCycle).where(ScholarshipCycle.scheme_id == scheme.id)
        )
        assert cycle is not None
        result = EligibilityService(session).evaluate_scholarship(
            profile=StudentEligibilityInput(evaluation_year=2025),
            cycle_id=cycle.id,
            evaluated_at=EVALUATED_AT,
        )
        assert result.decision.status is EligibilityStatus.NEEDS_INFORMATION
        assert result.decision.missing_information
