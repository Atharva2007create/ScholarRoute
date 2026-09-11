from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class SourceContext:
    authority_code: str
    authority_name: str
    official_domain: str
    source_url: str
    title: str
    academic_year: int
    importer_version: str = "1.0.0"


@dataclass(frozen=True)
class ParsedRecord:
    locator: str
    values: dict[str, Any]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class IngestionSummary:
    source: str
    parsed: int
    validated: int
    rejected: int
    published: int
    duplicate: bool = False
    run_id: UUID | None = None


class Importer(Protocol):
    kind: str
    version: str

    def parse(self, path: Path) -> list[ParsedRecord]: ...

    def normalize(self, record: ParsedRecord) -> dict[str, Any]: ...

    def validate(self, record: dict[str, Any]) -> list[ValidationIssue]: ...
