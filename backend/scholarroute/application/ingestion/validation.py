from __future__ import annotations

from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from scholarroute.application.ingestion.contracts import ValidationIssue

COMMERCIAL_AGGREGATORS = {"careers360.com", "shiksha.com", "collegedunia.com", "buddy4study.com"}


def validate_official_url(value: Any, field: str) -> list[ValidationIssue]:
    if not value:
        return [ValidationIssue("URL_REQUIRED", "An official URL is required", field)]
    parsed = urlparse(str(value))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return [ValidationIssue("URL_INVALID", "URL must be an absolute HTTP(S) URL", field)]
    host = (parsed.hostname or "").lower()
    if any(host == domain or host.endswith(f".{domain}") for domain in COMMERCIAL_AGGREGATORS):
        return [
            ValidationIssue(
                "SOURCE_NOT_AUTHORITATIVE", "Commercial aggregators are not authoritative", field
            )
        ]
    return []


def validate_admission_record(record: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in (
        "institution_code",
        "institution_name",
        "program_code",
        "program_name",
        "exam_code",
        "authority_code",
        "round_code",
        "category_code",
        "quota_code",
        "gender_pool_code",
        "source_locator",
    ):
        if not record.get(field):
            issues.append(ValidationIssue("FIELD_REQUIRED", f"{field} is required", field))
    year = record.get("academic_year")
    if not isinstance(year, int) or not 2000 <= year <= 2100:
        issues.append(
            ValidationIssue(
                "YEAR_INVALID", "Academic year must be between 2000 and 2100", "academic_year"
            )
        )
    opening = record.get("opening_rank")
    closing = record.get("closing_rank")
    if not isinstance(opening, int) or opening <= 0:
        issues.append(
            ValidationIssue("OPENING_RANK_INVALID", "Opening rank must be positive", "opening_rank")
        )
    if not isinstance(closing, int) or closing <= 0:
        issues.append(
            ValidationIssue("CLOSING_RANK_INVALID", "Closing rank must be positive", "closing_rank")
        )
    if isinstance(opening, int) and isinstance(closing, int) and opening > closing:
        issues.append(
            ValidationIssue(
                "RANK_ORDER_INVALID", "Opening rank cannot exceed closing rank", "opening_rank"
            )
        )
    seats = record.get("seat_count")
    if not isinstance(seats, int) or seats < 0:
        issues.append(
            ValidationIssue("SEAT_COUNT_INVALID", "Seat count cannot be negative", "seat_count")
        )
    for field in ("institution_url", "admissions_url", "counselling_url"):
        issues.extend(validate_official_url(record.get(field), field))
    return issues


def validate_scholarship_record(record: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in (
        "provider_code",
        "provider_name",
        "scheme_code",
        "scheme_name",
        "rule_version",
        "source_locator",
    ):
        if not record.get(field):
            issues.append(ValidationIssue("FIELD_REQUIRED", f"{field} is required", field))
    year = record.get("academic_year")
    if not isinstance(year, int) or not 2000 <= year <= 2100:
        issues.append(
            ValidationIssue(
                "YEAR_INVALID", "Academic year must be between 2000 and 2100", "academic_year"
            )
        )
    for field in ("income_max", "benefit_amount"):
        value = record.get(field)
        if value is not None and (not isinstance(value, Decimal) or value < 0):
            issues.append(ValidationIssue("VALUE_NEGATIVE", f"{field} cannot be negative", field))
    marks = record.get("minimum_marks")
    if marks is not None and (
        not isinstance(marks, Decimal) or not Decimal(0) <= marks <= Decimal(100)
    ):
        issues.append(
            ValidationIssue("PERCENTAGE_INVALID", "Minimum marks must be 0-100", "minimum_marks")
        )
    start = record.get("application_start_date")
    deadline = record.get("deadline")
    if start and deadline and start > deadline:
        issues.append(
            ValidationIssue(
                "DATE_ORDER_INVALID",
                "Application start cannot follow deadline",
                "application_start_date",
            )
        )
    for field in ("scheme_url", "application_url", "guidelines_url"):
        issues.extend(validate_official_url(record.get(field), field))
    return issues
