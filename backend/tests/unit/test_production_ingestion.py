import json
from pathlib import Path

import pytest

from scholarroute.application.ingestion.production_sources import (
    _mcc_records,
    josaa_records_from_documents,
    load_manifest,
    parse_josaa_institutions,
    parse_josaa_seats,
    scholarship_record_from_text,
)


def test_source_manifest_is_machine_readable_and_marks_blocked_source() -> None:
    manifest = load_manifest(Path("data/production/manifest.json"))
    assert manifest.manifest_version == "1.0"
    assert {source.data_domain for source in manifest.sources} >= {
        "engineering_cutoffs",
        "medical_seats",
        "scholarships",
    }
    blocked = [source for source in manifest.sources if source.status == "BLOCKED"]
    assert [source.source_id for source in blocked] == ["pm-usp-csss-2025-26"]


def test_josaa_html_adapters_preserve_codes_and_join_seats() -> None:
    institutions_html = """
    <table><tr><th>View Details</th><th>S.No.</th><th>Institute Code and Name</th>
    <th>Address</th><th>Phone/ Fax / Website</th></tr>
    <tr><td>View</td><td>1</td><td>201 National Institute of Technology Example</td>
    <td>Example, Maharashtra</td><td>Website: www.example.ac.in</td></tr></table>
    """
    seats_html = """
    <table><tr><th>Institute Name</th><th>Program Name</th><th>State/All India Seats</th>
    <th>Seat Pool</th><th>OPEN</th><th>OPEN-PwD</th><th>GEN-EWS</th>
    <th>GEN-EWS-PwD</th><th>SC</th><th>SC-PwD</th><th>ST</th><th>ST-PwD</th>
    <th>OBC-NCL</th><th>OBC-NCL-PwD</th></tr>
    <tr><th>Seat Capacity</th><th>Female Supernumerary</th></tr>
    <tr><td>National Institute of Technology Example</td>
    <td>Computer Science and Engineering (4 Years, Bachelor of Technology)</td>
    <td>All India</td><td>Gender-Neutral</td><td>10</td><td>0</td><td>2</td>
    <td>0</td><td>2</td><td>0</td><td>1</td><td>0</td><td>3</td><td>0</td></tr>
    </table>
    """
    ranks_html = """
    <select id="ddlInstitute"><option value="201">
    National Institute of Technology Example</option></select>
    <select id="ddlBranch"><option value="4110">
    Computer Science and Engineering (4 Years, Bachelor of Technology)</option></select>
    <table><tr><th>Institute</th><th>Academic Program Name</th><th>Quota</th>
    <th>Seat Type</th><th>Gender</th><th>Opening Rank</th><th>Closing Rank</th></tr>
    <tr><td>National Institute of Technology Example</td>
    <td>Computer Science and Engineering (4 Years, Bachelor of Technology)</td>
    <td>AI</td><td>OPEN</td><td>Gender-Neutral</td><td>100</td><td>200</td></tr>
    </table>
    """
    institutions = parse_josaa_institutions(institutions_html)
    seats = parse_josaa_seats(seats_html)
    records, warnings = josaa_records_from_documents(
        {"NIT.html": ranks_html}, institutions, seats, 2026, 5
    )
    assert warnings == []
    assert len(records) == 1
    assert records[0]["institution_code"] == "JOSAA_201"
    assert records[0]["program_code"] == "JOSAA_4110"
    assert records[0]["seat_count"] == 10
    assert records[0]["exam_code"] == "JEE_MAIN"


def test_mcc_pdf_adapter_joins_official_seat_and_result_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seat_path = Path("seat.pdf")
    result_path = Path("result.pdf")
    seat_table = [
        [
            "StateName",
            "InstituteType",
            "Institute",
            "Quota",
            "Branch",
            "Category",
            "TotalSeats",
            "SeatGender",
        ],
        [
            "Delhi",
            "All India except Central University",
            "Official Medical College\nAddress (200001)",
            "All India",
            "MBBS (MBBS)",
            "OP NO",
            "15",
            "Both",
        ],
    ]
    result_table = [
        [
            "SNo",
            "Rank",
            "Allotted Quota",
            "Allotted Institute",
            "Course",
            "Alloted Category",
            "Candidate Category",
            "Remarks",
        ],
        [
            "1",
            "100",
            "All India",
            "Official Medical College\nAddress",
            "MBBS",
            "Open",
            "General",
            "Allotted",
        ],
        [
            "2",
            "250",
            "All India",
            "Official Medical College\nAddress",
            "MBBS",
            "Open",
            "General",
            "Allotted",
        ],
    ]

    def fake_tables(path: Path) -> list[tuple[int, list[list[str]]]]:
        return [(1, seat_table if path == seat_path else result_table)]

    monkeypatch.setattr(
        "scholarroute.application.ingestion.production_sources._pdf_tables", fake_tables
    )
    records, warnings = _mcc_records(seat_path, result_path, 2026, 1)
    assert warnings == []
    assert len(records) == 1
    assert records[0]["institution_code"] == "MCC_200001"
    assert records[0]["opening_rank"] == 100
    assert records[0]["closing_rank"] == 250
    assert records[0]["seat_count"] == 15


def test_scholarship_adapter_requires_grounded_official_values() -> None:
    source_text = """
    Scheme of Top Class Scholarship for SC Students
    annual family income from all sources up to Rs. 8.00 lakh
    Academic allowance of Rs. 86,000 in the first year
    """
    record = scholarship_record_from_text(source_text, 2026)
    assert record["income_max"] == 800000
    assert record["eligible_category_codes"] == ["SC"]
    with pytest.raises(ValueError, match="missing expected text"):
        scholarship_record_from_text(json.dumps({"scheme": "unverified"}), 2026)
