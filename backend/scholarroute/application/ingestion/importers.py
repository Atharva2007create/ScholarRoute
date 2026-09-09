from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from scholarroute.application.ingestion.contracts import ParsedRecord, ValidationIssue
from scholarroute.application.ingestion.normalization import (
    normalize_admission_record,
    normalize_scholarship_record,
)
from scholarroute.application.ingestion.validation import (
    validate_admission_record,
    validate_scholarship_record,
)


def _read_csv(path: Path) -> list[ParsedRecord]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [
            ParsedRecord(locator=f"row:{row_number}", values=dict(row))
            for row_number, row in enumerate(csv.DictReader(stream), start=2)
        ]


def _read_json(path: Path) -> list[ParsedRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("JSON input must be a list of objects or an object containing records")
    return [
        ParsedRecord(locator=f"record:{index}", values=dict(row))
        for index, row in enumerate(rows, start=1)
    ]


def _read_xlsx(path: Path) -> list[ParsedRecord]:
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall("x:si", namespace)]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    table: list[list[Any]] = []
    for row in sheet.findall(".//x:row", namespace):
        values: dict[int, Any] = {}
        for cell in row.findall("x:c", namespace):
            reference = cell.attrib.get("r", "A1")
            letters = re.match(r"[A-Z]+", reference)
            if letters is None:
                continue
            column = 0
            for letter in letters.group(0):
                column = column * 26 + ord(letter) - ord("A") + 1
            value_node = cell.find("x:v", namespace)
            inline_node = cell.find("x:is", namespace)
            raw = (
                value_node.text
                if value_node is not None
                else "".join(inline_node.itertext())
                if inline_node is not None
                else ""
            )
            raw_text = raw or ""
            if cell.attrib.get("t") == "s" and raw:
                value: Any = shared[int(raw_text)]
            elif cell.attrib.get("t") in {"inlineStr", "str"}:
                value = raw
            elif raw_text == "":
                value = None
            else:
                try:
                    value = int(raw_text)
                except ValueError:
                    try:
                        value = float(raw_text)
                    except ValueError:
                        value = raw
            values[column - 1] = value
        width = max(values, default=-1) + 1
        table.append([values.get(index) for index in range(width)])
    if not table:
        return []
    headers = [str(value).strip() for value in table[0]]
    return [
        ParsedRecord(
            locator=f"sheet1!row:{row_number}",
            values={
                header: values[index] if index < len(values) else None
                for index, header in enumerate(headers)
            },
        )
        for row_number, values in enumerate(table[1:], start=2)
    ]


def read_structured_file(path: Path) -> list[ParsedRecord]:
    readers = {".csv": _read_csv, ".json": _read_json, ".xlsx": _read_xlsx}
    try:
        reader = readers[path.suffix.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported structured input format: {path.suffix}") from exc
    return reader(path)


class AdmissionImporter:
    kind = "admission"
    version = "1.0.0"

    def parse(self, path: Path) -> list[ParsedRecord]:
        return read_structured_file(path)

    def normalize(self, record: ParsedRecord) -> dict[str, Any]:
        values = normalize_admission_record(record.values)
        values["source_locator"] = record.values.get("source_locator") or record.locator
        return values

    def validate(self, record: dict[str, Any]) -> list[ValidationIssue]:
        return validate_admission_record(record)


class JoSAAImporter(AdmissionImporter):
    source_code = "JOSAA"


class MCCImporter(AdmissionImporter):
    source_code = "MCC"


class ScholarshipImporter:
    kind = "scholarship"
    version = "1.0.0"
    source_code = "NSP"

    def parse(self, path: Path) -> list[ParsedRecord]:
        return read_structured_file(path)

    def normalize(self, record: ParsedRecord) -> dict[str, Any]:
        values = normalize_scholarship_record(record.values)
        values["source_locator"] = record.values.get("source_locator") or record.locator
        return values

    def validate(self, record: dict[str, Any]) -> list[ValidationIssue]:
        return validate_scholarship_record(record)


class CSABImporter(JoSAAImporter):
    source_code = "CSAB"


class NMCImporter(MCCImporter):
    source_code = "NMC"


class NSPImporter(ScholarshipImporter):
    source_code = "NSP"


class AICTEImporter(ScholarshipImporter):
    source_code = "AICTE"
