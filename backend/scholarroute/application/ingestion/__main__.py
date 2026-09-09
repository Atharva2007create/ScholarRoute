from __future__ import annotations

import argparse
from pathlib import Path

from scholarroute.application.ingestion.contracts import Importer, SourceContext
from scholarroute.application.ingestion.importers import JoSAAImporter, MCCImporter, NSPImporter
from scholarroute.application.ingestion.service import run_ingestion
from scholarroute.infrastructure.db.session import session_scope

SOURCE_DEFAULTS: dict[str, tuple[type[Importer], str, str, str]] = {
    "josaa": (JoSAAImporter, "JOSAA", "Joint Seat Allocation Authority", "josaa.nic.in"),
    "mcc": (MCCImporter, "MCC", "Medical Counselling Committee", "mcc.nic.in"),
    "scholarship": (NSPImporter, "NSP", "National Scholarship Portal", "scholarships.gov.in"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest an authoritative structured dataset")
    parser.add_argument("kind", choices=SOURCE_DEFAULTS)
    parser.add_argument("path", type=Path)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--title", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    importer_type, code, name, domain = SOURCE_DEFAULTS[args.kind]
    context = SourceContext(
        authority_code=code,
        authority_name=name,
        official_domain=domain,
        source_url=args.source_url,
        title=args.title,
        academic_year=args.year,
    )
    with session_scope() as session:
        summary = run_ingestion(
            session,
            importer=importer_type(),
            path=args.path,
            context=context,
        )
    print(f"Source: {summary.source}")
    print(f"Parsed: {summary.parsed}")
    print(f"Validated: {summary.validated}")
    print(f"Rejected: {summary.rejected}")
    print(f"Published: {summary.published}")
    if summary.duplicate:
        print("Idempotent replay: existing ingestion run reused")


if __name__ == "__main__":
    main()
