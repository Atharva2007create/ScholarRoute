from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from scholarroute.application.ingestion.contracts import (
    Importer,
    IngestionSummary,
    SourceContext,
)
from scholarroute.application.ingestion.importers import JoSAAImporter, MCCImporter, NSPImporter
from scholarroute.application.ingestion.production_sources import (
    DEFAULT_MANIFEST,
    PREPARED_DIRECTORY,
    RAW_DIRECTORY,
    ProductionSource,
    fetch_sources,
    load_manifest,
    prepare_sources,
)
from scholarroute.application.ingestion.service import promote_ingestion_run, run_ingestion
from scholarroute.infrastructure.db.models import (
    AdmissionCycle,
    Branch,
    CutoffObservation,
    IngestionRun,
    Institution,
    Program,
    ProgramOffering,
    ResourceLink,
    ScholarshipCycle,
    ScholarshipEligibilityRule,
    ScholarshipProvider,
    ScholarshipScheme,
    SeatMatrixEntry,
    StagedRecord,
    ValidationFinding,
)
from scholarroute.infrastructure.db.models.enums import FindingSeverity
from scholarroute.infrastructure.db.session import session_scope


def _source(source_id: str) -> ProductionSource:
    manifest = load_manifest()
    return next(source for source in manifest.sources if source.source_id == source_id)


def _jobs() -> tuple[tuple[Path, Importer, SourceContext], ...]:
    josaa = _source("josaa-orcr-2026-r5")
    mcc = _source("mcc-ug-seats-2026-r1")
    scholarship = _source("dosje-top-class-sc-2026")
    return (
        (
            PREPARED_DIRECTORY / "josaa-2026.json",
            JoSAAImporter(),
            SourceContext(
                authority_code=josaa.authority_code,
                authority_name=josaa.authority,
                official_domain="josaa.nic.in",
                source_url=josaa.resource_url,
                title=josaa.source_name,
                academic_year=josaa.academic_year,
                importer_version="production-1.0.0",
            ),
        ),
        (
            PREPARED_DIRECTORY / "mcc-2026.json",
            MCCImporter(),
            SourceContext(
                authority_code=mcc.authority_code,
                authority_name=mcc.authority,
                official_domain="mcc.nic.in",
                source_url=mcc.resource_url,
                title=mcc.source_name,
                academic_year=mcc.academic_year,
                importer_version="production-1.0.0",
            ),
        ),
        (
            PREPARED_DIRECTORY / "scholarships-2026.json",
            NSPImporter(),
            SourceContext(
                authority_code=scholarship.authority_code,
                authority_name=scholarship.authority,
                official_domain="socialjustice.gov.in",
                source_url=scholarship.resource_url,
                title=scholarship.source_name,
                academic_year=scholarship.academic_year,
                importer_version="production-1.0.0",
            ),
        ),
    )


def _validated_counts(path: Path, importer: Importer) -> tuple[int, int]:
    parsed = importer.parse(path)
    valid = 0
    rejected = 0
    for record in parsed:
        try:
            normalized = importer.normalize(record)
            issues = importer.validate(normalized)
        except (KeyError, TypeError, ValueError):
            rejected += 1
            continue
        if issues:
            rejected += 1
        else:
            valid += 1
    return valid, rejected


def validate_prepared() -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for path, importer, _ in _jobs():
        valid, rejected = _validated_counts(path, importer)
        result[path.name] = {"validated": valid, "rejected": rejected}
    return result


def stage_prepared() -> tuple[IngestionSummary, ...]:
    summaries: list[IngestionSummary] = []
    with session_scope() as session:
        for path, importer, context in _jobs():
            summaries.append(
                run_ingestion(
                    session,
                    importer=importer,
                    path=path,
                    context=context,
                    publish=False,
                )
            )
    return tuple(summaries)


def promote_prepared() -> tuple[IngestionSummary, ...]:
    staged = stage_prepared()
    promoted: list[IngestionSummary] = []
    with session_scope() as session:
        for summary in staged:
            if summary.run_id is None:
                raise RuntimeError("staging did not return an ingestion run ID")
            promoted.append(promote_ingestion_run(session, summary.run_id))
    return tuple(promoted)


def _count(session: Any, model: Any, *criteria: Any) -> int:
    statement = select(func.count()).select_from(model)
    for criterion in criteria:
        statement = statement.where(criterion)
    return int(session.scalar(statement) or 0)


def coverage_metrics() -> dict[str, Any]:
    with session_scope() as session:
        engineering_institutions = _count(session, Institution, Institution.code.like("JOSAA_%"))
        medical_institutions = _count(session, Institution, Institution.code.like("MCC_%"))
        engineering_programs = _count(
            session,
            Program,
            Program.institution_id.in_(
                select(Institution.id).where(Institution.code.like("JOSAA_%"))
            ),
        )
        medical_programs = _count(
            session,
            Program,
            Program.institution_id.in_(
                select(Institution.id).where(Institution.code.like("MCC_%"))
            ),
        )
        metrics = {
            "engineering": {
                "institutions": engineering_institutions,
                "programs": engineering_programs,
                "branches": _count(session, Branch, Branch.code.like("JOSAA_%")),
                "cutoff_rows": _count(
                    session,
                    CutoffObservation,
                    CutoffObservation.offering_id.in_(
                        select(ProgramOffering.id)
                        .join(Program, Program.id == ProgramOffering.program_id)
                        .join(Institution, Institution.id == Program.institution_id)
                        .where(Institution.code.like("JOSAA_%"))
                    ),
                ),
                "seat_rows": _count(session, SeatMatrixEntry),
                "years": list(
                    session.scalars(
                        select(AdmissionCycle.academic_year)
                        .distinct()
                        .order_by(AdmissionCycle.academic_year)
                    )
                ),
            },
            "medical": {
                "institutions": medical_institutions,
                "mbbs_programs": medical_programs,
                "cutoff_admission_rows": _count(
                    session,
                    CutoffObservation,
                    CutoffObservation.offering_id.in_(
                        select(ProgramOffering.id)
                        .join(Program, Program.id == ProgramOffering.program_id)
                        .join(Institution, Institution.id == Program.institution_id)
                        .where(Institution.code.like("MCC_%"))
                    ),
                ),
            },
            "scholarships": {
                "providers": _count(session, ScholarshipProvider),
                "schemes": _count(session, ScholarshipScheme),
                "cycles": _count(session, ScholarshipCycle),
                "rules": _count(session, ScholarshipEligibilityRule),
            },
            "quality": {
                "ingestion_runs": _count(session, IngestionRun),
                "records_staged": _count(session, StagedRecord),
                "validation_errors": _count(
                    session,
                    ValidationFinding,
                    ValidationFinding.severity == FindingSeverity.ERROR,
                ),
                "official_links": _count(session, ResourceLink),
                "institutions_missing_url": _count(
                    session, Institution, Institution.official_url.is_(None)
                ),
            },
        }
    return metrics


def write_coverage_report(path: Path = Path("docs/production-data-coverage.md")) -> Path:
    manifest = load_manifest()
    metrics = coverage_metrics()
    lines = [
        "# Production data coverage",
        "",
        (
            "Generated from canonical PostgreSQL data and the checked-in authoritative "
            "source manifest."
        ),
        "",
        "## Sources",
        "",
        "| Source | Authority | Domain | Year | Format | Status | Last retrieved | Notes |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for source in manifest.sources:
        lines.append(
            "| "
            + " | ".join(
                (
                    source.source_name,
                    source.authority,
                    source.data_domain,
                    str(source.academic_year),
                    source.source_format,
                    source.status,
                    source.retrieved_at or "not retrieved",
                    source.notes.replace("|", "\\|"),
                )
            )
            + " |"
        )
    lines.extend(
        ["", "## Canonical coverage", "", "```json", json.dumps(metrics, indent=2), "```", ""]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _print_sources(sources: Iterable[ProductionSource]) -> None:
    for source in sources:
        print(
            f"{source.source_id}: {source.status} {source.source_format} "
            f"{source.academic_year} {source.resource_url}"
        )


def _print_summaries(summaries: Iterable[IngestionSummary]) -> None:
    for summary in summaries:
        payload = asdict(summary)
        if payload["run_id"] is not None:
            payload["run_id"] = str(payload["run_id"])
        print(json.dumps(payload, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="ScholarRoute authoritative production data")
    parser.add_argument(
        "command",
        choices=("discover", "fetch", "parse", "validate", "stage", "promote", "coverage", "run"),
    )
    args = parser.parse_args()
    if args.command == "discover":
        _print_sources(load_manifest(DEFAULT_MANIFEST).sources)
    elif args.command == "fetch":
        _print_sources(fetch_sources(DEFAULT_MANIFEST, RAW_DIRECTORY).sources)
    elif args.command == "parse":
        print(json.dumps(asdict(prepare_sources()), indent=2))
    elif args.command == "validate":
        print(json.dumps(validate_prepared(), indent=2))
    elif args.command == "stage":
        _print_summaries(stage_prepared())
    elif args.command == "promote":
        _print_summaries(promote_prepared())
    elif args.command == "coverage":
        report = write_coverage_report()
        print(report)
    else:
        _print_sources(fetch_sources().sources)
        print(json.dumps(asdict(prepare_sources()), indent=2))
        print(json.dumps(validate_prepared(), indent=2))
        _print_summaries(promote_prepared())
        print(write_coverage_report())


if __name__ == "__main__":
    main()
