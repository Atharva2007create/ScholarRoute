from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from scholarroute.application.ingestion.contracts import (
    Importer,
    IngestionSummary,
    SourceContext,
)
from scholarroute.application.ingestion.lifecycle import transition
from scholarroute.application.ingestion.reference_data import load_reference_data
from scholarroute.infrastructure.db.models import (
    AcademicYear,
    AdmissionCycle,
    Branch,
    Category,
    CounsellingAuthority,
    CounsellingRound,
    Course,
    CutoffObservation,
    DataSource,
    Exam,
    GenderPool,
    IngestionRun,
    Institution,
    InstitutionType,
    Program,
    ProgramOffering,
    QuotaType,
    ResourceLink,
    ScholarshipBenefit,
    ScholarshipCycle,
    ScholarshipEligibilityRule,
    ScholarshipProvider,
    ScholarshipScheme,
    SeatMatrixEntry,
    SeatType,
    SourceAuthority,
    SourceDocument,
    SourceDocumentVersion,
    StagedRecord,
    State,
    ValidationFinding,
)
from scholarroute.infrastructure.db.models.enums import (
    AdmissionCycleStatus,
    DataSourceType,
    FindingSeverity,
    IngestionRunStatus,
    ResourceEntityType,
    ResourceLinkType,
    ScholarshipProviderType,
    ScholarshipStatus,
    StagedRecordStatus,
)

ModelT = TypeVar("ModelT")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    return value


def _one_by(  # noqa: UP047
    session: Session, model: type[ModelT], **criteria: object
) -> ModelT | None:
    statement = select(model)
    for name, value in criteria.items():
        statement = statement.where(getattr(model, name) == value)
    return session.scalar(statement)


def _reference(  # noqa: UP047
    session: Session, model: type[ModelT], code: str
) -> ModelT:
    item = _one_by(session, model, code=code)
    if item is None:
        raise ValueError(f"Unknown canonical {model.__name__} code: {code}")
    return item


def _ensure_source(
    session: Session, context: SourceContext, path: Path, checksum: str
) -> tuple[SourceAuthority, DataSource, SourceDocumentVersion]:
    authority = _one_by(session, SourceAuthority, code=context.authority_code)
    if authority is None:
        authority = SourceAuthority(
            code=context.authority_code,
            name=context.authority_name,
            official_domain=context.official_domain,
        )
        session.add(authority)
        session.flush()
    source = _one_by(session, DataSource, canonical_url=context.source_url)
    if source is None:
        source = DataSource(
            authority_id=authority.id,
            authority_name=context.authority_name,
            canonical_url=context.source_url,
            source_type=DataSourceType.DATASET,
            trust_tier=1,
            retrieval_policy={"mode": "manual_official_fixture"},
        )
        session.add(source)
        session.flush()
    document = _one_by(
        session, SourceDocument, data_source_id=source.id, canonical_uri=context.source_url
    )
    if document is None:
        media_types = {
            ".csv": "text/csv",
            ".json": "application/json",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        document = SourceDocument(
            data_source_id=source.id,
            canonical_uri=context.source_url,
            title=context.title,
            academic_year=context.academic_year,
            media_type=media_types[path.suffix.lower()],
        )
        session.add(document)
        session.flush()
    version = _one_by(
        session, SourceDocumentVersion, document_id=document.id, content_hash=checksum
    )
    if version is None:
        version = SourceDocumentVersion(
            document_id=document.id,
            content_hash=checksum,
            retrieved_at=datetime.now(UTC),
            storage_uri=f"fixture://{checksum}/{path.name}",
            parser_version=context.importer_version,
            http_metadata={"source_url": context.source_url, "local_fixture": True},
        )
        session.add(version)
        session.flush()
    return authority, source, version


def _ensure_link(
    session: Session,
    *,
    entity_type: ResourceEntityType,
    entity_id: object,
    link_type: ResourceLinkType,
    url: str,
    authority_id: object,
    academic_year: int | None,
    source_version_id: object,
) -> None:
    existing = _one_by(
        session,
        ResourceLink,
        entity_type=entity_type,
        entity_id=entity_id,
        link_type=link_type,
        url=url,
        academic_year=academic_year,
    )
    if existing is None:
        session.add(
            ResourceLink(
                entity_type=entity_type,
                entity_id=entity_id,
                link_type=link_type,
                url=url,
                source_authority_id=authority_id,
                academic_year=academic_year,
                verified_at=datetime.now(UTC),
                is_active=True,
                source_document_version_id=source_version_id,
            )
        )


def _publish_admission(
    session: Session,
    record: dict[str, Any],
    authority: SourceAuthority,
    source_version: SourceDocumentVersion,
) -> UUID:
    year = int(record["academic_year"])
    if _one_by(session, AcademicYear, year=year) is None:
        session.add(AcademicYear(year=year, label=f"{year}-{str(year + 1)[-2:]}"))
    state = _reference(session, State, str(record["state_code"]))
    institution_type = _reference(session, InstitutionType, str(record["institution_type_code"]))
    institution = _one_by(session, Institution, code=record["institution_code"])
    if institution is None:
        institution = Institution(
            code=record["institution_code"],
            official_name=record["institution_name"],
            institution_type_id=institution_type.id,
            state_id=state.id,
            official_url=record["institution_url"],
            official_identifier=record.get("official_identifier"),
            ownership_type=record.get("ownership_type"),
        )
        session.add(institution)
        session.flush()
    course = _reference(session, Course, str(record["course_code"]))
    branch = _one_by(session, Branch, code=record["branch_code"])
    if branch is None:
        branch = Branch(code=record["branch_code"], name=record["branch_name"], course_id=course.id)
        session.add(branch)
        session.flush()
    program = _one_by(session, Program, institution_id=institution.id, code=record["program_code"])
    if program is None:
        program = Program(
            institution_id=institution.id,
            course_id=course.id,
            branch_id=branch.id,
            code=record["program_code"],
            name=record["program_name"],
        )
        session.add(program)
        session.flush()
    counselling = _one_by(session, CounsellingAuthority, code=record["authority_code"])
    if counselling is None:
        counselling = CounsellingAuthority(
            code=record["authority_code"],
            name=record["authority_name"],
            official_url=record["counselling_url"],
        )
        session.add(counselling)
        session.flush()
    exam = _reference(session, Exam, str(record["exam_code"]))
    cycle = _one_by(
        session,
        AdmissionCycle,
        authority_id=counselling.id,
        exam_id=exam.id,
        academic_year=year,
        scope_state_id=None,
    )
    if cycle is None:
        cycle = AdmissionCycle(
            authority_id=counselling.id,
            exam_id=exam.id,
            academic_year=year,
            status=AdmissionCycleStatus.CLOSED,
        )
        session.add(cycle)
        session.flush()
    round_ = _one_by(
        session, CounsellingRound, admission_cycle_id=cycle.id, code=record["round_code"]
    )
    if round_ is None:
        round_ = CounsellingRound(
            admission_cycle_id=cycle.id,
            code=record["round_code"],
            name=record["round_name"],
            sequence=record["round_sequence"],
        )
        session.add(round_)
        session.flush()
    quota = _reference(session, QuotaType, str(record["quota_code"]))
    category = _reference(session, Category, str(record["category_code"]))
    gender = _reference(session, GenderPool, str(record["gender_pool_code"]))
    seat_type = _reference(session, SeatType, str(record.get("seat_type_code", "REGULAR")))
    offering = _one_by(
        session,
        ProgramOffering,
        admission_cycle_id=cycle.id,
        program_id=program.id,
        quota_type_id=quota.id,
        category_id=category.id,
        gender_pool_id=gender.id,
        seat_type_id=seat_type.id,
    )
    if offering is None:
        offering = ProgramOffering(
            admission_cycle_id=cycle.id,
            program_id=program.id,
            quota_type_id=quota.id,
            category_id=category.id,
            gender_pool_id=gender.id,
            seat_type_id=seat_type.id,
            source_document_version_id=source_version.id,
            original_values=_json_safe(record),
        )
        session.add(offering)
        session.flush()
    cutoff = _one_by(
        session,
        CutoffObservation,
        offering_id=offering.id,
        round_id=round_.id,
        rank_type=record.get("rank_type", "CRL"),
        source_document_version_id=source_version.id,
    )
    if cutoff is None:
        cutoff = CutoffObservation(
            offering_id=offering.id,
            round_id=round_.id,
            rank_type=record.get("rank_type", "CRL"),
            opening_rank=record["opening_rank"],
            closing_rank=record["closing_rank"],
            source_document_version_id=source_version.id,
            source_locator=record["source_locator"],
        )
        session.add(cutoff)
        session.flush()
    if (
        _one_by(
            session,
            SeatMatrixEntry,
            offering_id=offering.id,
            round_id=round_.id,
            source_document_version_id=source_version.id,
        )
        is None
    ):
        session.add(
            SeatMatrixEntry(
                offering_id=offering.id,
                round_id=round_.id,
                seat_count=record["seat_count"],
                source_document_version_id=source_version.id,
                source_locator=record["source_locator"],
            )
        )
    for entity_type, entity_id, link_type, url in (
        (
            ResourceEntityType.INSTITUTION,
            institution.id,
            ResourceLinkType.OFFICIAL_WEBSITE,
            record["institution_url"],
        ),
        (
            ResourceEntityType.PROGRAM,
            program.id,
            ResourceLinkType.ADMISSIONS_PAGE,
            record["admissions_url"],
        ),
        (
            ResourceEntityType.COUNSELLING_AUTHORITY,
            counselling.id,
            ResourceLinkType.COUNSELLING_PAGE,
            record["counselling_url"],
        ),
    ):
        _ensure_link(
            session,
            entity_type=entity_type,
            entity_id=entity_id,
            link_type=link_type,
            url=url,
            authority_id=authority.id,
            academic_year=year,
            source_version_id=source_version.id,
        )
    return cutoff.id


def _publish_scholarship(
    session: Session,
    record: dict[str, Any],
    authority: SourceAuthority,
    source_version: SourceDocumentVersion,
) -> UUID:
    provider = _one_by(session, ScholarshipProvider, code=record["provider_code"])
    if provider is None:
        provider = ScholarshipProvider(
            code=record["provider_code"],
            name=record["provider_name"],
            provider_type=ScholarshipProviderType(record["provider_type"]),
        )
        session.add(provider)
        session.flush()
    scheme = _one_by(
        session,
        ScholarshipScheme,
        provider_id=provider.id,
        official_code=record["scheme_code"],
    )
    if scheme is None:
        scheme = ScholarshipScheme(
            provider_id=provider.id,
            official_code=record["scheme_code"],
            name=record["scheme_name"],
            description=record.get("description"),
        )
        session.add(scheme)
        session.flush()
    year = int(record["academic_year"])
    cycle = _one_by(
        session,
        ScholarshipCycle,
        scheme_id=scheme.id,
        academic_year=year,
        rule_version=record["rule_version"],
    )
    if cycle is None:
        cycle = ScholarshipCycle(
            scheme_id=scheme.id,
            academic_year=year,
            rule_version=record["rule_version"],
            status=ScholarshipStatus(record["status"]),
            application_start_date=record.get("application_start_date"),
            deadline=record.get("deadline"),
            source_document_version_id=source_version.id,
        )
        session.add(cycle)
        session.flush()
        session.add(
            ScholarshipEligibilityRule(
                cycle_id=cycle.id,
                income_max=record.get("income_max"),
                minimum_marks=record.get("minimum_marks"),
                achievement_code=record.get("achievement_code") or None,
                achievement_minimum=record.get("achievement_minimum") or None,
                achievement_unit=record.get("achievement_unit") or None,
                conditions_summary=record.get("conditions_summary", ""),
                source_locator=record.get("source_locator"),
            )
        )
        session.add(
            ScholarshipBenefit(
                cycle_id=cycle.id,
                benefit_type=record.get("benefit_type", "GRANT"),
                amount_min=record.get("benefit_amount"),
                amount_max=record.get("benefit_amount"),
                frequency=record.get("benefit_frequency") or None,
                description=record.get("benefit_description", "Financial assistance"),
            )
        )
    for link_type, url in (
        (ResourceLinkType.SCHOLARSHIP_PAGE, record["scheme_url"]),
        (ResourceLinkType.APPLICATION_PAGE, record["application_url"]),
        (ResourceLinkType.GUIDELINES_PAGE, record["guidelines_url"]),
    ):
        _ensure_link(
            session,
            entity_type=ResourceEntityType.SCHOLARSHIP,
            entity_id=scheme.id,
            link_type=link_type,
            url=url,
            authority_id=authority.id,
            academic_year=year,
            source_version_id=source_version.id,
        )
    return cycle.id


def run_ingestion(
    session: Session,
    *,
    importer: Importer,
    path: Path,
    context: SourceContext,
) -> IngestionSummary:
    content = path.read_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    idempotency_key = f"{context.authority_code}:{importer.kind}:{context.academic_year}:{checksum}"
    existing = _one_by(session, IngestionRun, idempotency_key=idempotency_key)
    if existing is not None:
        return IngestionSummary(
            source=context.authority_code,
            parsed=existing.records_parsed,
            validated=existing.records_validated,
            rejected=existing.records_rejected,
            published=existing.records_published,
            duplicate=True,
        )

    load_reference_data(session)
    authority, source, source_version = _ensure_source(session, context, path, checksum)
    run = IngestionRun(
        data_source_id=source.id,
        source_document_version_id=source_version.id,
        idempotency_key=idempotency_key,
        trigger="CLI",
        connector_version=importer.version,
        parser_version=importer.version,
        academic_year=context.academic_year,
        source_filename=path.name,
        checksum=checksum,
        started_at=datetime.now(UTC),
        status=IngestionRunStatus.RECEIVED,
    )
    session.add(run)
    session.flush()

    parsed_records = importer.parse(path)
    run.records_discovered = len(parsed_records)
    run.records_parsed = len(parsed_records)
    run.status = IngestionRunStatus.PARSED
    for index, parsed in enumerate(parsed_records, start=1):
        staged = StagedRecord(
            ingestion_run_id=run.id,
            entity_type=importer.kind,
            record_key=f"{checksum}:{index}",
            raw_payload=_json_safe(parsed.values),
            source_locator=parsed.locator,
            status=StagedRecordStatus.RAW,
        )
        session.add(staged)
        session.flush()
        try:
            staged.status = transition(staged.status, StagedRecordStatus.PARSED)
            normalized = importer.normalize(parsed)
            staged.normalized_payload = _json_safe(normalized)
            staged.status = transition(staged.status, StagedRecordStatus.NORMALIZED)
            issues = importer.validate(normalized)
        except (KeyError, TypeError, ValueError) as exc:
            issues = []
            session.add(
                ValidationFinding(
                    staged_record_id=staged.id,
                    rule_code="NORMALIZATION_ERROR",
                    severity=FindingSeverity.ERROR,
                    message=str(exc),
                )
            )
        if issues:
            for issue in issues:
                session.add(
                    ValidationFinding(
                        staged_record_id=staged.id,
                        rule_code=issue.code,
                        severity=FindingSeverity.ERROR,
                        field_name=issue.field,
                        message=issue.message,
                    )
                )
        if issues or staged.normalized_payload is None:
            staged.status = transition(staged.status, StagedRecordStatus.REJECTED)
            run.records_rejected += 1
            continue
        staged.status = transition(staged.status, StagedRecordStatus.VALIDATED)
        run.records_validated += 1
        entity_id = (
            _publish_admission(session, normalized, authority, source_version)
            if importer.kind == "admission"
            else _publish_scholarship(session, normalized, authority, source_version)
        )
        staged.published_entity_id = entity_id
        staged.status = transition(staged.status, StagedRecordStatus.PUBLISHED)
        run.records_published += 1

    run.completed_at = datetime.now(UTC)
    run.status = (
        IngestionRunStatus.PUBLISHED
        if run.records_published
        else IngestionRunStatus.VALIDATION_FAILED
    )
    run.metrics = {
        "discovered": run.records_discovered,
        "parsed": run.records_parsed,
        "validated": run.records_validated,
        "published": run.records_published,
        "rejected": run.records_rejected,
    }
    return IngestionSummary(
        source=context.authority_code,
        parsed=run.records_parsed,
        validated=run.records_validated,
        rejected=run.records_rejected,
        published=run.records_published,
    )
