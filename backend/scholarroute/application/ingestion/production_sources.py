from __future__ import annotations

import hashlib
import html
import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import httpx

from scholarroute.application.ingestion.normalization import (
    normalize_category,
    normalize_gender_pool,
    normalize_quota,
    normalize_state,
)

RAW_DIRECTORY = Path("data/production/raw")
PREPARED_DIRECTORY = Path("data/production/prepared")
DEFAULT_MANIFEST = Path("data/production/manifest.json")


@dataclass(frozen=True)
class ProductionSource:
    source_id: str
    source_name: str
    authority: str
    authority_code: str
    official_base_url: str
    resource_url: str
    data_domain: str
    admission_route: str | None
    academic_year: int
    counselling_round: int | None
    source_format: str
    retrieval_method: str
    local_filename: str
    effective_from: str | None
    effective_to: str | None
    retrieved_at: str | None
    checksum: str | None
    license_or_usage_note: str
    status: str
    notes: str


@dataclass(frozen=True)
class SourceManifest:
    manifest_version: str
    generated_at: str | None
    sources: tuple[ProductionSource, ...]


@dataclass(frozen=True)
class PreparationSummary:
    engineering_records: int
    medical_records: int
    scholarship_records: int
    nmc_reference_records: int
    warnings: tuple[str, ...]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._rows = []
        elif self._table_depth == 1 and tag == "tr":
            self._row = []
        elif self._table_depth == 1 and tag in {"td", "th"}:
            self._cell = []
        elif self._cell is not None and tag in {"br", "p", "div"}:
            self._cell.append("\n")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._table_depth == 1 and tag in {"td", "th"} and self._cell is not None:
            if self._row is not None:
                self._row.append(_clean("".join(self._cell)))
            self._cell = None
        elif self._table_depth == 1 and tag == "tr" and self._row is not None:
            if any(self._row):
                self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            if self._table_depth == 1:
                self.tables.append(self._rows)
            self._table_depth -= 1


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _identity_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path = DEFAULT_MANIFEST) -> SourceManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SourceManifest(
        manifest_version=str(payload["manifest_version"]),
        generated_at=payload.get("generated_at"),
        sources=tuple(ProductionSource(**item) for item in payload["sources"]),
    )


def save_manifest(manifest: SourceManifest, path: Path = DEFAULT_MANIFEST) -> None:
    payload = {
        "manifest_version": manifest.manifest_version,
        "generated_at": manifest.generated_at,
        "sources": [source.__dict__ for source in manifest.sources],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _hidden_fields(document: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for tag in re.findall(r"<input[^>]+>", document, re.IGNORECASE):
        name = re.search(r'name="([^"]+)"', tag, re.IGNORECASE)
        kind = re.search(r'type="([^"]+)"', tag, re.IGNORECASE)
        value = re.search(r'value="([^"]*)"', tag, re.IGNORECASE)
        if name and (kind is None or kind.group(1).lower() == "hidden"):
            fields[name.group(1)] = html.unescape(value.group(1) if value else "")
    return fields


def _postback(
    client: httpx.Client,
    url: str,
    document: str,
    target: str,
    values: dict[str, str],
) -> str:
    payload = _hidden_fields(document)
    payload.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
    payload.update(values)
    response = client.post(url, data=payload)
    response.raise_for_status()
    if "Something Went Wrong" in response.text:
        raise RuntimeError(f"official JoSAA form rejected postback for {target}")
    return response.text


def _fetch_josaa_orcr(source: ProductionSource, destination: Path) -> None:
    values = {
        "ctl00$ContentPlaceHolder1$ddlroundno": str(source.counselling_round or 5),
    }
    with httpx.Client(follow_redirects=True, timeout=180) as client:
        initial = client.get(source.resource_url)
        initial.raise_for_status()
        for institute_type in ("IIT", "NIT", "3IT", "CFI"):
            document = _postback(
                client,
                source.resource_url,
                initial.text,
                "ctl00$ContentPlaceHolder1$ddlroundno",
                values,
            )
            typed = dict(values, **{"ctl00$ContentPlaceHolder1$ddlInstype": institute_type})
            document = _postback(
                client,
                source.resource_url,
                document,
                "ctl00$ContentPlaceHolder1$ddlInstype",
                typed,
            )
            selected = dict(typed, **{"ctl00$ContentPlaceHolder1$ddlInstitute": "ALL"})
            document = _postback(
                client,
                source.resource_url,
                document,
                "ctl00$ContentPlaceHolder1$ddlInstitute",
                selected,
            )
            selected["ctl00$ContentPlaceHolder1$ddlBranch"] = "ALL"
            document = _postback(
                client,
                source.resource_url,
                document,
                "ctl00$ContentPlaceHolder1$ddlBranch",
                selected,
            )
            selected["ctl00$ContentPlaceHolder1$ddlSeattype"] = "ALL"
            payload = _hidden_fields(document)
            payload.update(selected)
            payload["ctl00$ContentPlaceHolder1$btnSubmit"] = "Submit"
            response = client.post(source.resource_url, data=payload)
            response.raise_for_status()
            if "GridView1" not in response.text or "Something Went Wrong" in response.text:
                raise RuntimeError(f"JoSAA returned no rank table for {institute_type}")
            if institute_type == "IIT":
                archive = ZipFile(destination, mode="w", compression=ZIP_DEFLATED)
            else:
                archive = ZipFile(destination, mode="a", compression=ZIP_DEFLATED)
            with archive:
                archive.writestr(f"{institute_type}.html", response.content)
            time.sleep(0.5)


def _fetch_josaa_seats(source: ProductionSource, destination: Path) -> None:
    with httpx.Client(follow_redirects=True, timeout=180) as client:
        response = client.get(source.resource_url)
        response.raise_for_status()
        payload = _hidden_fields(response.text)
        payload.update(
            {
                "ctl00$ContentPlaceHolder1$ddlInstType": "0",
                "ctl00$ContentPlaceHolder1$ddlInstitute": "0",
                "ctl00$ContentPlaceHolder1$ddlBranch": "0",
                "ctl00$ContentPlaceHolder1$btnSubmit": "Submit",
            }
        )
        response = client.post(source.resource_url, data=payload)
        response.raise_for_status()
        if "GridView" not in response.text or "Something Went Wrong" in response.text:
            raise RuntimeError("JoSAA returned no seat-matrix table")
        destination.write_bytes(response.content)


def fetch_sources(
    manifest_path: Path = DEFAULT_MANIFEST,
    raw_directory: Path = RAW_DIRECTORY,
) -> SourceManifest:
    manifest = load_manifest(manifest_path)
    raw_directory.mkdir(parents=True, exist_ok=True)
    updated: list[ProductionSource] = []
    for source in manifest.sources:
        destination = raw_directory / source.local_filename
        try:
            if (
                source.status == "FETCHED"
                and source.checksum is not None
                and destination.exists()
                and _sha256(destination) == source.checksum
            ):
                updated.append(source)
                continue
            if source.retrieval_method == "MANUAL_DOWNLOAD":
                if not destination.exists():
                    updated.append(source)
                    continue
            elif source.source_id == "josaa-orcr-2026-r5":
                destination = destination.with_suffix(".zip")
                _fetch_josaa_orcr(source, destination)
            elif source.source_id == "josaa-seats-2026":
                _fetch_josaa_seats(source, destination)
            else:
                verify = source.source_id != "nmc-mbbs-seats-2026"
                response = httpx.get(
                    source.resource_url,
                    follow_redirects=True,
                    timeout=180,
                    verify=verify,
                )
                response.raise_for_status()
                destination.write_bytes(response.content)
                notes = source.notes
                if not verify:
                    notes += (
                        " Local TLS chain validation is unavailable; the URL was verified on "
                        "the official NMC page before retrieval."
                    )
                    source = replace(source, notes=notes)
            updated.append(
                replace(
                    source,
                    local_filename=destination.name,
                    retrieved_at=datetime.now(UTC).isoformat(),
                    checksum=_sha256(destination),
                    status="FETCHED",
                )
            )
        except (httpx.HTTPError, OSError, RuntimeError) as exc:
            updated.append(replace(source, status="BLOCKED", notes=f"{source.notes} {exc}"))
    result = SourceManifest(
        manifest_version=manifest.manifest_version,
        generated_at=datetime.now(UTC).isoformat(),
        sources=tuple(updated),
    )
    save_manifest(result, manifest_path)
    return result


def _tables(document: str) -> list[list[list[str]]]:
    parser = _TableParser()
    parser.feed(document)
    return parser.tables


def _table_with(document: str, required: set[str]) -> list[list[str]]:
    for table in _tables(document):
        if table and required <= {cell for cell in table[0]}:
            return table
    raise ValueError(f"expected table columns not found: {sorted(required)}")


def _select_options(document: str, select_fragment: str) -> dict[str, str]:
    match = re.search(
        rf'<select[^>]+(?:id|name)="[^"]*{select_fragment}[^"]*"[^>]*>(.*?)</select>',
        document,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return {}
    return {
        _clean(re.sub(r"<.*?>", "", label)): value
        for value, label in re.findall(
            r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>',
            match.group(1),
            re.IGNORECASE | re.DOTALL,
        )
        if value not in {"0", "ALL"}
    }


_STATE_NAMES = tuple(
    sorted(
        {
            "Andaman and Nicobar Islands",
            "Andhra Pradesh",
            "Arunachal Pradesh",
            "Assam",
            "Bihar",
            "Chandigarh",
            "Chhattisgarh",
            "Chattisgarh",
            "Delhi",
            "Goa",
            "Gujarat",
            "Haryana",
            "Himachal Pradesh",
            "Jammu and Kashmir",
            "Jammu & Kashmir",
            "Jharkhand",
            "Karnataka",
            "Kerala",
            "Ladakh",
            "Madhya Pradesh",
            "Maharashtra",
            "Manipur",
            "Meghalaya",
            "Mizoram",
            "Nagaland",
            "Odisha",
            "Puducherry",
            "Punjab",
            "Rajasthan",
            "Sikkim",
            "Tamil Nadu",
            "Telangana",
            "Tripura",
            "Uttar Pradesh",
            "Uttarakhand",
            "West Bengal",
        },
        key=len,
        reverse=True,
    )
)


def _state_from_text(value: str) -> str | None:
    upper = value.upper()
    for name in _STATE_NAMES:
        if name.upper() in upper:
            return normalize_state(name)
    abbreviations = {" A.P ": "AP", " MP ": "MP", " J&K ": "JK"}
    padded = f" {upper} "
    return next((code for token, code in abbreviations.items() if token in padded), None)


def parse_josaa_institutions(document: str) -> dict[str, dict[str, str]]:
    table = _table_with(document, {"Institute Code and Name", "Address"})
    output: dict[str, dict[str, str]] = {}
    for row in table[1:]:
        if len(row) < 5:
            continue
        identity = row[2]
        match = re.match(r"(\d{3})\s+(.+)", identity)
        if match is None:
            continue
        code, name = match.groups()
        state_code = _state_from_text(row[3])
        if state_code is None:
            continue
        website_match = re.search(
            r"Website:\s*((?:https?://)?(?:www\.)?[A-Za-z0-9.-]+(?:/[^\s,]*)?)",
            row[4],
            re.IGNORECASE,
        )
        website = website_match.group(1).rstrip("./") if website_match else ""
        if website and not website.startswith(("http://", "https://")):
            website = f"https://{website}"
        output[_clean(name)] = {
            "code": code,
            "name": _clean(name),
            "state_code": state_code,
            "website": website,
            "address": row[3],
        }
    return output


_JOSAA_TYPE = {"1": "IIT", "2": "NIT", "3": "IIIT", "4": "GFTI"}
_JOSAA_EXAM = {"1": "JEE_ADVANCED", "2": "JEE_MAIN", "3": "JEE_MAIN", "4": "JEE_MAIN"}
_SEAT_CATEGORIES = (
    "OPEN",
    "OPEN_PWD",
    "EWS",
    "EWS_PWD",
    "SC",
    "SC_PWD",
    "ST",
    "ST_PWD",
    "OBC_NCL",
    "OBC_NCL_PWD",
)


def parse_josaa_seats(document: str) -> dict[tuple[str, str, str, str, str], int]:
    table = _table_with(document, {"Institute Name", "Program Name", "Seat Pool"})
    output: dict[tuple[str, str, str, str, str], int] = {}
    context: tuple[str, str, str] | None = None
    for row in table[2:]:
        if len(row) >= 14 and row[0] not in {"Seat Capacity", "Female Supernumerary"}:
            context = (_clean(row[0]), _clean(row[1]), normalize_quota(row[2]))
            gender = normalize_gender_pool(row[3])
            values = row[4:14]
        elif context is not None and row and "Female-only" in row[0]:
            gender = normalize_gender_pool(row[0])
            values = row[1:11]
        else:
            continue
        if len(values) != 10:
            continue
        for category, value in zip(_SEAT_CATEGORIES, values, strict=True):
            if str(value).strip().isdigit():
                output[(*context, category, gender)] = int(value)
    return output


def _josaa_records(
    archive_path: Path,
    institutions: dict[str, dict[str, str]],
    seats: dict[tuple[str, str, str, str, str], int],
    year: int,
    round_sequence: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    with ZipFile(archive_path) as archive:
        documents = {
            entry: archive.read(entry).decode("utf-8-sig", errors="replace")
            for entry in archive.namelist()
        }
    return josaa_records_from_documents(documents, institutions, seats, year, round_sequence)


def josaa_records_from_documents(
    documents: dict[str, str],
    institutions: dict[str, dict[str, str]],
    seats: dict[tuple[str, str, str, str, str], int],
    year: int,
    round_sequence: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    for entry, document in documents.items():
        institute_codes = _select_options(document, "ddlInstitute")
        program_codes = _select_options(document, "ddlBranch")
        table = _table_with(
            document,
            {"Institute", "Academic Program Name", "Opening Rank", "Closing Rank"},
        )
        for row_number, row in enumerate(table[1:], start=2):
            if len(row) < 7 or "Bachelor of Technology" not in row[1]:
                continue
            institution_name, program_name, quota, category, gender, opening, closing = row[:7]
            profile = institutions.get(_clean(institution_name))
            institute_code = institute_codes.get(_clean(institution_name))
            program_code = program_codes.get(_clean(program_name))
            if profile is None or institute_code is None or program_code is None:
                warnings.append(f"unresolved JoSAA identity at {entry}:row:{row_number}")
                continue
            opening_text = opening.rstrip("P")
            closing_text = closing.rstrip("P")
            if not opening_text.isdigit() or not closing_text.isdigit():
                warnings.append(f"invalid JoSAA rank at {entry}:row:{row_number}")
                continue
            canonical_category = normalize_category(category.replace(" (PwD)", "-PwD"))
            canonical_quota = normalize_quota(quota)
            canonical_gender = normalize_gender_pool(gender)
            seat_count = seats.get(
                (
                    _clean(institution_name),
                    _clean(program_name),
                    canonical_quota,
                    canonical_category,
                    canonical_gender,
                )
            )
            if seat_count is None:
                warnings.append(f"missing JoSAA seat match at {entry}:row:{row_number}")
                seat_count = 0
            branch_name = _clean(program_name.split("(", 1)[0])
            prefix = institute_code[0]
            profile_url = "https://josaa.admissions.nic.in/applicant/seatmatrix/instituteview.aspx"
            records.append(
                {
                    "academic_year": year,
                    "institution_code": f"JOSAA_{institute_code}",
                    "institution_name": profile["name"],
                    "institution_type_code": _JOSAA_TYPE[prefix],
                    "state": profile["state_code"],
                    "institution_url": profile["website"] or profile_url,
                    "official_identifier": institute_code,
                    "ownership_type": "PUBLIC",
                    "course_code": "BTECH",
                    "branch_code": f"JOSAA_{program_code}",
                    "branch_name": branch_name,
                    "program_code": f"JOSAA_{program_code}",
                    "program_name": program_name,
                    "exam_code": _JOSAA_EXAM[prefix],
                    "authority_code": "JOSAA",
                    "authority_name": "Joint Seat Allocation Authority",
                    "round_code": f"R{round_sequence}",
                    "round_name": f"Round {round_sequence}",
                    "round_sequence": round_sequence,
                    "category": canonical_category,
                    "quota": canonical_quota,
                    "gender_pool": canonical_gender,
                    "seat_type_code": "REGULAR",
                    "rank_type": "CRL" if canonical_category.startswith("OPEN") else "CATEGORY",
                    "opening_rank": int(opening_text),
                    "closing_rank": int(closing_text),
                    "seat_count": seat_count,
                    "admissions_url": profile_url,
                    "counselling_url": (
                        "https://josaa.admissions.nic.in/Applicant/SeatAllotmentResult/"
                        "currentorcr.aspx"
                    ),
                    "source_locator": f"{entry}:table-row:{row_number}",
                    "identity_source_locator": profile_url,
                    "source_program_name": program_name,
                    "admission_requirement_summary": (
                        f"Admission route recorded by JoSAA {year} for this programme."
                    ),
                }
            )
    return records, warnings


def _pdf_tables(path: Path) -> list[tuple[int, list[list[str | None]]]]:
    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "PDF ingestion requires the project ingestion extra: pip install -e .[ingestion]"
        ) from exc
    output: list[tuple[int, list[list[str | None]]]] = []
    with pdfplumber.open(path) as document:
        for page_number, page in enumerate(document.pages, start=1):
            for table in page.extract_tables():
                output.append((page_number, table))
    return output


def _mcc_category(value: str) -> str:
    token = _clean(value).upper().replace("GENERAL-EWS", "EWS")
    mapping = {
        "OP": "OPEN",
        "OPEN": "OPEN",
        "GN": "OPEN",
        "BC": "OBC_NCL",
        "OBC": "OBC_NCL",
        "EW": "EWS",
    }
    base = next(
        (mapped for key, mapped in mapping.items() if token.startswith(key)),
        normalize_category(token),
    )
    return f"{base}_PWD" if any(marker in token for marker in (" PH", "PWD")) else base


def _mcc_institute(value: str) -> tuple[str, str]:
    cleaned = _clean(value)
    code_match = re.search(r"\((\d{6})\)\s*$", cleaned)
    code = code_match.group(1) if code_match else ""
    without_code = re.sub(r"\s*\(\d{6}\)\s*$", "", cleaned)
    first_line = _clean(str(value).splitlines()[0])
    return code, (first_line or without_code)[:255]


def _mcc_records(
    seat_path: Path,
    result_path: Path,
    year: int,
    round_sequence: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    cutoffs: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for _, table in _pdf_tables(result_path):
        for row in table:
            if len(row) != 8 or not _clean(row[0]).isdigit() or not _clean(row[1]).isdigit():
                continue
            if _clean(row[4]).upper() != "MBBS" or _clean(row[7]).upper() != "ALLOTTED":
                continue
            institution = _clean(str(row[3] or "").splitlines()[0])
            key = (
                _identity_key(institution),
                normalize_quota(_clean(row[2])),
                _mcc_category(_clean(row[5])),
            )
            cutoffs[key].append(int(_clean(row[1])))
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    source_page = "https://mcc.nic.in/current-events-ug/"
    for page_number, table in _pdf_tables(seat_path):
        for row_number, row in enumerate(table, start=1):
            if len(row) != 8 or _clean(row[4]).upper() != "MBBS (MBBS)":
                continue
            code, name = _mcc_institute(str(row[2] or ""))
            if not code or not _clean(row[6]).isdigit():
                warnings.append(
                    f"unparseable MCC seat identity at page:{page_number}:row:{row_number}"
                )
                continue
            quota = normalize_quota(_clean(row[3]))
            category = _mcc_category(_clean(row[5]))
            key = (_identity_key(name), quota, category)
            ranks = cutoffs.get(key)
            if not ranks:
                continue
            institute_type_text = _clean(row[1]).upper()
            if "DEEMED" in institute_type_text:
                institution_type = "DEEMED_UNIVERSITY"
                ownership = "PRIVATE"
            elif any(token in institute_type_text for token in ("PRIVATE", "SELF")):
                institution_type = "MEDICAL_PRIVATE"
                ownership = "PRIVATE"
            else:
                institution_type = "MEDICAL_GOVERNMENT"
                ownership = "PUBLIC"
            records.append(
                {
                    "academic_year": year,
                    "institution_code": f"MCC_{code}",
                    "institution_name": name,
                    "institution_type_code": institution_type,
                    "state": normalize_state(_clean(row[0])),
                    "institution_url": source_page,
                    "official_identifier": code,
                    "ownership_type": ownership,
                    "course_code": "MBBS",
                    "branch_code": "MBBS_GENERAL",
                    "branch_name": "MBBS",
                    "program_code": "MBBS",
                    "program_name": "MBBS",
                    "exam_code": "NEET_UG",
                    "authority_code": "MCC",
                    "authority_name": "Medical Counselling Committee",
                    "round_code": f"R{round_sequence}",
                    "round_name": f"Round {round_sequence}",
                    "round_sequence": round_sequence,
                    "category": category,
                    "quota": quota,
                    "gender_pool": "GENDER_NEUTRAL",
                    "seat_type_code": "REGULAR",
                    "rank_type": "CRL",
                    "opening_rank": min(ranks),
                    "closing_rank": max(ranks),
                    "seat_count": int(_clean(row[6])),
                    "admissions_url": source_page,
                    "counselling_url": source_page,
                    "source_locator": (
                        f"seat-page:{page_number}:row:{row_number};result-ranks:{len(ranks)}"
                    ),
                    "source_institute_type": _clean(row[1]),
                    "source_category": _clean(row[5]),
                    "admission_requirement_summary": (
                        f"NEET UG route recorded by MCC {year} for this MBBS programme."
                    ),
                }
            )
    return records, warnings


def parse_nmc_reference_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for page_number, table in _pdf_tables(path):
        for row_number, row in enumerate(table, start=1):
            if len(row) != 8 or not _clean(row[0]).isdigit():
                continue
            code = _clean(row[2])
            total = _clean(row[7])
            if not code or not total.isdigit():
                continue
            records.append(
                {
                    "state": _clean(row[1]),
                    "college_code": code,
                    "college_name": _clean(row[3]),
                    "management": _clean(row[4]),
                    "seats_renewed": _clean(row[5]),
                    "seats_increased": _clean(row[6]),
                    "total_seats": int(total),
                    "source_locator": f"page:{page_number}:row:{row_number}",
                }
            )
    return records


def scholarship_record_from_text(text: str, year: int) -> dict[str, Any]:
    lowered = text.lower()
    required = (
        "Scheme of Top Class Scholarship for SC Students",
        "Academic allowance of Rs. 86,000 in the first year",
    )
    missing = [phrase for phrase in required if phrase.lower() not in lowered]
    if "annual family income from all sources up to rs. 8.00 lakh" not in lowered and (
        "total annual family income from all sources up to rs. 8.00" not in lowered
    ):
        missing.append("annual family income from all sources up to Rs. 8.00 lakh")
    if missing:
        raise ValueError(f"scholarship source is missing expected text: {missing}")
    scheme_url = "https://socialjustice.gov.in/schemes/27"
    return {
        "academic_year": year,
        "provider_code": "DOSJE",
        "provider_name": "Department of Social Justice and Empowerment",
        "provider_type": "CENTRAL_GOVERNMENT",
        "scheme_code": "TOP_CLASS_SC",
        "scheme_name": "Central Sector Scholarship of Top Class Education for SC Students",
        "description": (
            "Financial support for eligible SC students studying beyond Class 12 in "
            "notified institutions."
        ),
        "rule_version": "applicable-from-2025-26",
        "status": "PUBLISHED",
        "income_max": 800000,
        "minimum_marks": None,
        "conditions_summary": (
            "SC student; annual family income up to INR 8 lakh; full-time prescribed course "
            "in a notified institution; fresh awards are for first-year students."
        ),
        "benefit_type": "GRANT",
        "benefit_amount": 86000,
        "benefit_frequency": "FIRST_YEAR_ACADEMIC_ALLOWANCE",
        "benefit_description": (
            "Full tuition and non-refundable charges (private-sector ceiling INR 2 lakh per "
            "year) plus INR 86,000 first-year academic allowance; later-year allowance differs."
        ),
        "application_start_date": None,
        "deadline": None,
        "scheme_url": scheme_url,
        "application_url": "https://scholarships.gov.in/",
        "guidelines_url": (
            "https://socialjustice.gov.in/writereaddata/UploadFile/81931782276781.pdf"
        ),
        "eligible_category_codes": ["SC"],
        "source_locator": "pages:1-3;eligibility:section-2;funding:section-4",
    }


def _scholarship_record(path: Path, year: int) -> dict[str, Any]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "PDF ingestion requires the project ingestion extra: pip install -e .[ingestion]"
        ) from exc
    with pdfplumber.open(path) as document:
        text = "\n".join(page.extract_text() or "" for page in document.pages)
    return scholarship_record_from_text(text, year)


def _source(manifest: SourceManifest, source_id: str) -> ProductionSource:
    return next(source for source in manifest.sources if source.source_id == source_id)


def prepare_sources(
    manifest_path: Path = DEFAULT_MANIFEST,
    raw_directory: Path = RAW_DIRECTORY,
    prepared_directory: Path = PREPARED_DIRECTORY,
) -> PreparationSummary:
    manifest = load_manifest(manifest_path)
    prepared_directory.mkdir(parents=True, exist_ok=True)
    institutes_source = _source(manifest, "josaa-institutes-2026")
    ranks_source = _source(manifest, "josaa-orcr-2026-r5")
    seats_source = _source(manifest, "josaa-seats-2026")
    institutes_path = raw_directory / institutes_source.local_filename
    ranks_path = raw_directory / ranks_source.local_filename
    seats_path = raw_directory / seats_source.local_filename
    institutions = parse_josaa_institutions(institutes_path.read_text(encoding="utf-8-sig"))
    seats = parse_josaa_seats(seats_path.read_text(encoding="utf-8-sig"))
    engineering, engineering_warnings = _josaa_records(
        ranks_path,
        institutions,
        seats,
        ranks_source.academic_year,
        ranks_source.counselling_round or 5,
    )
    mcc_seats = _source(manifest, "mcc-ug-seats-2026-r1")
    mcc_result = _source(manifest, "mcc-ug-result-2026-r1")
    medical, medical_warnings = _mcc_records(
        raw_directory / mcc_seats.local_filename,
        raw_directory / mcc_result.local_filename,
        mcc_seats.academic_year,
        mcc_seats.counselling_round or 1,
    )
    nmc = _source(manifest, "nmc-mbbs-seats-2026")
    nmc_records = parse_nmc_reference_records(raw_directory / nmc.local_filename)
    scholarship = _source(manifest, "dosje-top-class-sc-2026")
    scholarships = [
        _scholarship_record(raw_directory / scholarship.local_filename, scholarship.academic_year)
    ]
    payloads = {
        "josaa-2026.json": {
            "source_id": ranks_source.source_id,
            "records": engineering,
        },
        "mcc-2026.json": {"source_id": mcc_seats.source_id, "records": medical},
        "scholarships-2026.json": {
            "source_id": scholarship.source_id,
            "records": scholarships,
        },
        "nmc-reference-2026.json": {"source_id": nmc.source_id, "records": nmc_records},
    }
    for filename, payload in payloads.items():
        (prepared_directory / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return PreparationSummary(
        engineering_records=len(engineering),
        medical_records=len(medical),
        scholarship_records=len(scholarships),
        nmc_reference_records=len(nmc_records),
        warnings=tuple(engineering_warnings + medical_warnings),
    )
