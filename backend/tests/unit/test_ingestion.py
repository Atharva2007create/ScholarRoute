from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from scholarroute.application.ingestion.importers import read_structured_file
from scholarroute.application.ingestion.lifecycle import transition
from scholarroute.application.ingestion.normalization import (
    normalize_admission_record,
    normalize_scholarship_record,
)
from scholarroute.application.ingestion.validation import (
    validate_admission_record,
    validate_official_url,
    validate_scholarship_record,
)
from scholarroute.infrastructure.db.models.enums import StagedRecordStatus

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_normalization_preserves_source_values_and_maps_aliases() -> None:
    normalized = normalize_admission_record(
        {
            "academic_year": "2025",
            "round_sequence": "1",
            "state": "Delhi (NCT)",
            "category": "OBC NCL",
            "quota": "All India",
            "gender_pool": "Gender Neutral",
            "opening_rank": "1,000",
            "closing_rank": "2,000",
            "seat_count": "10",
        }
    )
    assert normalized["category"] == "OBC NCL"
    assert normalized["category_code"] == "OBC_NCL"
    assert normalized["state_code"] == "DL"
    assert normalized["quota_code"] == "ALL_INDIA"
    assert normalized["opening_rank"] == 1000


def test_normalization_converts_scholarship_values() -> None:
    normalized = normalize_scholarship_record(
        {
            "academic_year": "2025",
            "provider_type": "Central Government",
            "income_max": "800000",
            "minimum_marks": "60",
            "benefit_amount": "50000",
            "application_start_date": "2025-07-01",
            "deadline": "2025-10-31",
        }
    )
    assert normalized["provider_type"] == "CENTRAL_GOVERNMENT"
    assert normalized["income_max"] == Decimal("800000")
    assert normalized["application_start_date"] == date(2025, 7, 1)


def test_invalid_records_and_urls_are_rejected() -> None:
    admission = {
        "academic_year": 2025,
        "institution_code": "X",
        "institution_name": "X",
        "program_code": "P",
        "program_name": "P",
        "exam_code": "JEE_MAIN",
        "authority_code": "JOSAA",
        "round_code": "R1",
        "category_code": "OPEN",
        "quota_code": "ALL_INDIA",
        "gender_pool_code": "GENDER_NEUTRAL",
        "source_locator": "row:1",
        "opening_rank": 500,
        "closing_rank": 100,
        "seat_count": -1,
        "institution_url": "https://example.gov.in",
        "admissions_url": "https://example.gov.in/admission",
        "counselling_url": "https://josaa.nic.in",
    }
    assert {issue.code for issue in validate_admission_record(admission)} >= {
        "RANK_ORDER_INVALID",
        "SEAT_COUNT_INVALID",
    }
    assert (
        validate_official_url("https://www.careers360.com/college", "url")[0].code
        == "SOURCE_NOT_AUTHORITATIVE"
    )
    assert validate_official_url("ftp://example.gov.in/file", "url")[0].code == "URL_INVALID"


def test_scholarship_validation_rejects_negative_income_and_bad_dates() -> None:
    record = {
        "provider_code": "X",
        "provider_name": "X",
        "scheme_code": "X",
        "scheme_name": "X",
        "rule_version": "v1",
        "source_locator": "row:1",
        "academic_year": 2025,
        "income_max": Decimal("-1"),
        "minimum_marks": Decimal("101"),
        "application_start_date": date(2025, 12, 1),
        "deadline": date(2025, 1, 1),
        "scheme_url": "https://scholarships.gov.in/scheme",
        "application_url": "https://scholarships.gov.in/apply",
        "guidelines_url": "https://scholarships.gov.in/guidelines",
    }
    assert {issue.code for issue in validate_scholarship_record(record)} >= {
        "VALUE_NEGATIVE",
        "PERCENTAGE_INVALID",
        "DATE_ORDER_INVALID",
    }


def test_structured_parsers_and_lifecycle() -> None:
    assert len(read_structured_file(FIXTURES / "josaa_2025_test.csv")) == 4
    assert len(read_structured_file(FIXTURES / "neet_2025_test.json")) == 3
    assert len(read_structured_file(FIXTURES / "scholarships_2025_test.xlsx")) == 3
    assert (
        transition(StagedRecordStatus.RAW, StagedRecordStatus.PARSED) is StagedRecordStatus.PARSED
    )
    with pytest.raises(ValueError):
        transition(StagedRecordStatus.PUBLISHED, StagedRecordStatus.REJECTED)
