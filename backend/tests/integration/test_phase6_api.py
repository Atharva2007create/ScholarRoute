from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from scholarroute.application.ai.service import AIExplanationService
from scholarroute.application.ingestion.contracts import SourceContext
from scholarroute.application.ingestion.importers import JoSAAImporter, MCCImporter, NSPImporter
from scholarroute.application.ingestion.service import run_ingestion
from scholarroute.config import Settings
from scholarroute.entrypoints.api.app import create_app
from scholarroute.entrypoints.api.dependencies import SessionDependency
from scholarroute.entrypoints.api.v1.ai import get_ai_explanation_service
from scholarroute.infrastructure.db.models import (
    AdmissionRequirement,
    Exam,
    Program,
    ScholarshipCycle,
    ScholarshipScheme,
    SourceDocument,
    SourceDocumentVersion,
)
from scholarroute.infrastructure.db.session import session_scope

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture(scope="module")
def phase6_data(migrated_database: str) -> dict[str, str]:
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
                title="JoSAA API fixture",
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
                title="MCC API fixture",
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
                title="NSP API fixture",
                academic_year=2025,
            ),
        )
        program = session.scalar(select(Program).where(Program.code == "TEST-IIT-DL-CSE"))
        exam = session.scalar(select(Exam).where(Exam.code == "JEE_MAIN"))
        source = session.scalar(
            select(SourceDocumentVersion)
            .join(SourceDocument)
            .where(SourceDocument.canonical_uri == "https://josaa.nic.in/test/2025.csv")
        )
        assert program is not None and exam is not None and source is not None
        requirement = session.scalar(
            select(AdmissionRequirement).where(AdmissionRequirement.code == "API-JEE-2025")
        )
        if requirement is None:
            session.add(
                AdmissionRequirement(
                    code="API-JEE-2025",
                    academic_year=2025,
                    exam_id=exam.id,
                    program_id=program.id,
                    minimum_marks=Decimal("60"),
                    rule_version="2025.1",
                    summary="API test eligibility",
                    source_locator="api-rules!page:1",
                    source_document_version_id=source.id,
                )
            )
        neet_program = session.scalar(select(Program).where(Program.code == "TEST-MED-RJ-MBBS"))
        neet_exam = session.scalar(select(Exam).where(Exam.code == "NEET_UG"))
        neet_source = session.scalar(
            select(SourceDocumentVersion)
            .join(SourceDocument)
            .where(SourceDocument.canonical_uri == "https://mcc.nic.in/test/2025.json")
        )
        assert neet_program is not None and neet_exam is not None and neet_source is not None
        if (
            session.scalar(
                select(AdmissionRequirement).where(AdmissionRequirement.code == "API-NEET-2025")
            )
            is None
        ):
            session.add(
                AdmissionRequirement(
                    code="API-NEET-2025",
                    academic_year=2025,
                    exam_id=neet_exam.id,
                    program_id=neet_program.id,
                    minimum_exam_score=Decimal("50"),
                    rule_version="2025.1",
                    summary="API NEET eligibility",
                    source_locator="neet-api!page:1",
                    source_document_version_id=neet_source.id,
                )
            )
        scheme = session.scalar(
            select(ScholarshipScheme).where(ScholarshipScheme.official_code == "NSP-TEST-MERIT")
        )
        assert scheme is not None
        cycle = session.scalar(
            select(ScholarshipCycle).where(ScholarshipCycle.scheme_id == scheme.id)
        )
        assert cycle is not None
        return {
            "program_id": str(program.id),
            "neet_program_id": str(neet_program.id),
            "cycle_id": str(cycle.id),
        }


@pytest.fixture()
def client(phase6_data: dict[str, str]) -> TestClient:
    del phase6_data
    return TestClient(create_app())


def student(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "evaluation_year": 2025,
        "exam_code": "JEE_MAIN",
        "exam_rank": 300,
        "category_code": "OPEN",
        "class12_percentage": 75,
    }
    payload.update(overrides)
    return payload


def test_reference_filter_pagination_and_openapi(client: TestClient) -> None:
    for resource in ("exams", "boards", "states", "categories", "courses"):
        assert client.get(f"/api/v1/reference/{resource}").status_code == 200
    exams = client.get("/api/v1/reference/exams?limit=1&offset=0")
    assert exams.status_code == 200
    assert exams.json()["meta"]["limit"] == 1
    course = client.get("/api/v1/reference/courses").json()["results"][0]
    branches = client.get(f"/api/v1/reference/branches/by-course/{course['id']}")
    assert branches.status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/eligibility/evaluate" in schema["paths"]
    assert "/api/v1/recommendations/colleges" in schema["paths"]


@pytest.mark.parametrize(
    ("marks", "expected"), [(75, "ELIGIBLE"), (50, "INELIGIBLE"), (None, "NEEDS_INFORMATION")]
)
def test_eligibility_three_states(
    client: TestClient, phase6_data: dict[str, str], marks: int | None, expected: str
) -> None:
    profile = student(class12_percentage=marks)
    response = client.post(
        "/api/v1/eligibility/evaluate",
        json={
            "subject_type": "PROGRAM",
            "subject_id": phase6_data["program_id"],
            "student": profile,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == expected
    assert body["reason_codes"]
    assert body["rules"][0]["evidence"]["official_url"]
    if expected == "NEEDS_INFORMATION":
        assert body["missing_information"]


def test_college_recommendations_ranking_links_and_pagination(client: TestClient) -> None:
    response = client.post(
        "/api/v1/recommendations/colleges",
        json={"student": student(), "preferences": {"preferred_branch_codes": ["CSE"]}, "limit": 1},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["limit"] == 1
    assert body["results"][0]["rank_position"] == 1
    assert body["results"][0]["tier"] in {"SAFER", "TARGET", "REACH", "INSUFFICIENT_DATA"}
    assert body["results"][0]["components"]
    assert body["results"][0]["official_links"]
    detail = client.get(f"/api/v1/recommendations/{body['meta']['ranking_run_id']}/1")
    assert detail.status_code == 200


def test_neet_style_eligibility_request(client: TestClient, phase6_data: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/eligibility/evaluate",
        json={
            "subject_type": "PROGRAM",
            "subject_id": phase6_data["neet_program_id"],
            "student": {
                "evaluation_year": 2025,
                "exam_code": "NEET_UG",
                "exam_score": 65,
                "exam_rank": 50000,
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ELIGIBLE"


def test_scholarship_recommendations_and_empty_filter(client: TestClient) -> None:
    response = client.post(
        "/api/v1/recommendations/scholarships",
        json={
            "student": {"evaluation_year": 2025, "class12_percentage": 75, "family_income": 500000}
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    assert any("apply" in link for link in body["results"][0]["official_links"])
    empty = client.post(
        "/api/v1/recommendations/scholarships",
        json={"student": {"evaluation_year": 2025}, "provider_code": "DOES_NOT_EXIST"},
    )
    assert empty.status_code == 200
    assert empty.json()["results"] == []


def test_validation_and_error_envelopes(client: TestClient) -> None:
    invalid = client.post(
        "/api/v1/recommendations/colleges",
        json={"student": {"evaluation_year": 2025, "exam_rank": -1}},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid.headers["X-Request-ID"]
    missing = client.get("/api/v1/reference/not-real")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_cors_is_restricted_to_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/reference/exams",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


class _GroundedFakeProvider:
    def generate(self, **values: Any) -> dict[str, object]:
        prompt = str(values["prompt"])
        return {
            "summary": "This explanation uses the stored ScholarRoute result.",
            "reasons": ["The deterministic result and its reason codes were supplied."],
            "caveats": ["Official authorities remain the final source."],
            "next_steps": [
                "Provide missing information."
                if "NEEDS_INFORMATION" in prompt
                else "Review the official information attached by ScholarRoute."
            ],
        }


def test_phase8_endpoints_use_persisted_authoritative_results(
    client: TestClient, phase6_data: dict[str, str]
) -> None:
    config = Settings(_env_file=None, AI_ENABLED=True, GEMINI_API_KEY="test-only")

    def override_service(session: SessionDependency) -> AIExplanationService:
        return AIExplanationService(session, config, _GroundedFakeProvider())

    client.app.dependency_overrides[get_ai_explanation_service] = override_service
    try:
        college = client.post(
            "/api/v1/recommendations/colleges",
            json={
                "student": student(),
                "preferences": {"preferred_branch_codes": ["CSE"]},
                "limit": 1,
            },
        ).json()
        college_ai = client.post(
            "/api/v1/ai/explain/college",
            json={
                "ranking_run_id": college["meta"]["ranking_run_id"],
                "rank_position": 1,
            },
        )
        assert college_ai.status_code == 200, college_ai.text
        assert college_ai.json()["authoritative"]["tier"] == college["results"][0]["tier"]
        assert Decimal(college_ai.json()["authoritative"]["fit_score"]) == Decimal(
            college["results"][0]["fit_score"]
        )
        assert college_ai.json()["official_links"] == college["results"][0]["official_links"]

        scholarship = client.post(
            "/api/v1/recommendations/scholarships",
            json={
                "student": {
                    "evaluation_year": 2025,
                    "class12_percentage": 75,
                    "family_income": 500000,
                }
            },
        ).json()
        scholarship_ai = client.post(
            "/api/v1/ai/explain/scholarship",
            json={
                "ranking_run_id": scholarship["meta"]["ranking_run_id"],
                "rank_position": 1,
            },
        )
        assert scholarship_ai.status_code == 200, scholarship_ai.text
        assert scholarship_ai.json()["authoritative"]["tier"] == scholarship["results"][0]["tier"]
        assert (
            scholarship_ai.json()["official_links"] == scholarship["results"][0]["official_links"]
        )

        for marks, expected in ((75, "ELIGIBLE"), (50, "INELIGIBLE"), (None, "NEEDS_INFORMATION")):
            eligibility = client.post(
                "/api/v1/eligibility/evaluate",
                json={
                    "subject_type": "PROGRAM",
                    "subject_id": phase6_data["program_id"],
                    "student": student(class12_percentage=marks),
                },
            ).json()
            explanation = client.post(
                "/api/v1/ai/explain/eligibility",
                json={"evaluation_id": eligibility["evaluation_id"]},
            )
            assert explanation.status_code == 200, explanation.text
            assert explanation.json()["authoritative"]["eligibility_status"] == expected
    finally:
        client.app.dependency_overrides.clear()
