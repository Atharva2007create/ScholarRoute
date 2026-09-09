from pathlib import Path

from sqlalchemy import func, select

from scholarroute.application.ingestion.contracts import SourceContext
from scholarroute.application.ingestion.importers import JoSAAImporter, MCCImporter, NSPImporter
from scholarroute.application.ingestion.service import run_ingestion
from scholarroute.infrastructure.db.models import (
    AdmissionCycle,
    CutoffObservation,
    IngestionRun,
    ResourceLink,
    SourceDocumentVersion,
    StagedRecord,
    ValidationFinding,
)
from scholarroute.infrastructure.db.session import session_scope

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_phase3_verticals_provenance_links_history_and_idempotency(migrated_database: str) -> None:
    del migrated_database
    with session_scope() as session:
        josaa = run_ingestion(
            session,
            importer=JoSAAImporter(),
            path=FIXTURES / "josaa_2025_test.csv",
            context=SourceContext(
                authority_code="JOSAA",
                authority_name="Joint Seat Allocation Authority",
                official_domain="josaa.nic.in",
                source_url="https://josaa.nic.in/test/2025.csv",
                title="JoSAA 2025 deterministic test fixture",
                academic_year=2025,
            ),
        )
        assert (josaa.parsed, josaa.validated, josaa.rejected, josaa.published) == (4, 3, 1, 3)
        replay = run_ingestion(
            session,
            importer=JoSAAImporter(),
            path=FIXTURES / "josaa_2025_test.csv",
            context=SourceContext(
                authority_code="JOSAA",
                authority_name="Joint Seat Allocation Authority",
                official_domain="josaa.nic.in",
                source_url="https://josaa.nic.in/test/2025.csv",
                title="JoSAA 2025 deterministic test fixture",
                academic_year=2025,
            ),
        )
        assert replay.duplicate is True
        assert replay.published == 3
        neet = run_ingestion(
            session,
            importer=MCCImporter(),
            path=FIXTURES / "neet_2025_test.json",
            context=SourceContext(
                authority_code="MCC",
                authority_name="Medical Counselling Committee",
                official_domain="mcc.nic.in",
                source_url="https://mcc.nic.in/test/2025.json",
                title="MCC 2025 deterministic test fixture",
                academic_year=2025,
            ),
        )
        assert (neet.parsed, neet.validated, neet.rejected, neet.published) == (3, 2, 1, 2)
        scholarship = run_ingestion(
            session,
            importer=NSPImporter(),
            path=FIXTURES / "scholarships_2025_test.xlsx",
            context=SourceContext(
                authority_code="NSP",
                authority_name="National Scholarship Portal",
                official_domain="scholarships.gov.in",
                source_url="https://scholarships.gov.in/test/2025.xlsx",
                title="NSP 2025 deterministic XLSX fixture",
                academic_year=2025,
            ),
        )
        assert (
            scholarship.parsed,
            scholarship.validated,
            scholarship.rejected,
            scholarship.published,
        ) == (3, 2, 1, 2)
        historical = run_ingestion(
            session,
            importer=JoSAAImporter(),
            path=FIXTURES / "josaa_2024_test.json",
            context=SourceContext(
                authority_code="JOSAA",
                authority_name="Joint Seat Allocation Authority",
                official_domain="josaa.nic.in",
                source_url="https://josaa.nic.in/test/2024.json",
                title="JoSAA 2024 deterministic test fixture",
                academic_year=2024,
            ),
        )
        assert historical.published == 1
        assert session.scalar(select(func.count()).select_from(AdmissionCycle)) == 3
        assert session.scalar(select(func.count()).select_from(CutoffObservation)) == 6
        assert session.scalar(select(func.count()).select_from(ResourceLink)) >= 12
        assert session.scalar(select(func.count()).select_from(SourceDocumentVersion)) == 4
        assert session.scalar(select(func.count()).select_from(ValidationFinding)) >= 3
        assert session.scalar(select(func.count()).select_from(StagedRecord)) == 11
        assert session.scalar(select(func.count()).select_from(IngestionRun)) == 4
