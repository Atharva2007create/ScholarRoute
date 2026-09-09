from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from scholarroute.domain.eligibility.models import (
    CandidateContext,
    EligibilitySubjectType,
    ReasonCode,
    RuleDefinition,
    RuleEvidence,
    RuleOperator,
    RuleScope,
    RuleSet,
    StudentEligibilityInput,
)
from scholarroute.infrastructure.db.models import (
    AdmissionCycle,
    AdmissionRequirement,
    AdmissionRequirementSubject,
    Board,
    Category,
    Course,
    Exam,
    GenderPool,
    InstitutionType,
    Program,
    QuotaType,
    ResourceLink,
    ScholarshipCycle,
    ScholarshipEligibilityRule,
    ScholarshipEligibleCategory,
    ScholarshipEligibleGenderPool,
    ScholarshipEligibleInstitutionType,
    ScholarshipEligibleProgram,
    ScholarshipEligibleState,
    ScholarshipRequiredDocument,
    ScholarshipScheme,
    SourceDocument,
    SourceDocumentVersion,
    State,
    Subject,
)
from scholarroute.infrastructure.db.models.enums import ResourceEntityType
from scholarroute.infrastructure.db.models.provenance import DataSource


class RuleSetNotFoundError(LookupError):
    pass


class InvalidStudentReferenceError(ValueError):
    pass


def _codes_by_id(
    session: Session,
    model: Any,
    identifiers: Iterable[UUID | None],
) -> dict[UUID, str]:
    ids = {identifier for identifier in identifiers if identifier is not None}
    if not ids:
        return {}
    return {item.id: item.code for item in session.scalars(select(model).where(model.id.in_(ids)))}


def validate_student_references(session: Session, profile: StudentEligibilityInput) -> None:
    checks: tuple[tuple[Any, str | None, str], ...] = (
        (Exam, profile.exam_code, "exam_code"),
        (Category, profile.category_code, "category_code"),
        (QuotaType, profile.quota_code, "quota_code"),
        (GenderPool, profile.gender_pool_code, "gender_pool_code"),
        (State, profile.state_code, "state_code"),
        (State, profile.domicile_state_code, "domicile_state_code"),
        (Board, profile.board_code, "board_code"),
        (Course, profile.target_course_code, "target_course_code"),
        (InstitutionType, profile.institution_type_code, "institution_type_code"),
    )
    for model, code, field_name in checks:
        if code is not None and session.scalar(select(model).where(model.code == code)) is None:
            raise InvalidStudentReferenceError(f"Unknown {field_name}: {code}")
    if (
        profile.target_program_id is not None
        and session.get(Program, profile.target_program_id) is None
    ):
        raise InvalidStudentReferenceError(
            f"Unknown target_program_id: {profile.target_program_id}"
        )
    subject_codes = set(profile.subjects_studied or ()) | set(profile.subject_marks or {})
    if subject_codes:
        known = set(session.scalars(select(Subject.code).where(Subject.code.in_(subject_codes))))
        unknown = sorted(subject_codes - known)
        if unknown:
            raise InvalidStudentReferenceError(f"Unknown subject codes: {unknown}")


def _evidence(
    session: Session,
    *,
    source_version_id: UUID,
    applicable_year: int,
    rule_version: str,
    source_locator: str | None,
) -> RuleEvidence:
    row = session.execute(
        select(SourceDocumentVersion, SourceDocument, DataSource)
        .join(SourceDocument, SourceDocument.id == SourceDocumentVersion.document_id)
        .join(DataSource, DataSource.id == SourceDocument.data_source_id)
        .where(SourceDocumentVersion.id == source_version_id)
    ).one()
    version, document, source = row
    return RuleEvidence(
        source_document_version_id=version.id,
        source_authority=source.authority_name,
        source_document=document.title,
        source_locator=source_locator,
        official_url=document.canonical_uri,
        applicable_year=applicable_year,
        rule_version=rule_version,
        verified_at=version.retrieved_at,
    )


def _official_links(
    session: Session,
    targets: Iterable[tuple[ResourceEntityType, UUID]],
    year: int,
) -> list[ResourceLink]:
    conditions = [
        (ResourceLink.entity_type == entity_type) & (ResourceLink.entity_id == entity_id)
        for entity_type, entity_id in targets
    ]
    if not conditions:
        return []
    return list(
        session.scalars(
            select(ResourceLink).where(
                or_(*conditions),
                ResourceLink.is_active.is_(True),
                or_(ResourceLink.academic_year == year, ResourceLink.academic_year.is_(None)),
            )
        )
    )


def _rule(
    *,
    requirement: AdmissionRequirement,
    suffix: str,
    operator: RuleOperator,
    field_name: str,
    expected: object,
    description: str,
    reasons: tuple[ReasonCode, ReasonCode, ReasonCode],
    scope: RuleScope,
    evidence: RuleEvidence,
) -> RuleDefinition:
    return RuleDefinition(
        rule_id=f"{requirement.code}:{suffix}",
        version=requirement.rule_version,
        key=f"admission:{suffix}",
        operator=operator,
        field_name=field_name,
        expected=expected,
        description=description,
        pass_reason=reasons[0],
        fail_reason=reasons[1],
        missing_reason=reasons[2],
        scope=scope,
        evidence=evidence,
    )


def load_program_rule_set(
    session: Session,
    *,
    profile: StudentEligibilityInput,
    program_id: UUID,
    rule_set_version: str | None = None,
) -> tuple[CandidateContext, RuleSet, list[ResourceLink]]:
    program = session.get(Program, program_id)
    if program is None:
        raise RuleSetNotFoundError(f"Program not found: {program_id}")
    statement = select(AdmissionRequirement).where(
        AdmissionRequirement.academic_year == profile.evaluation_year,
        or_(
            AdmissionRequirement.program_id == program.id,
            AdmissionRequirement.institution_id == program.institution_id,
            (
                AdmissionRequirement.program_id.is_(None)
                & AdmissionRequirement.institution_id.is_(None)
            ),
        ),
    )
    if rule_set_version is not None:
        statement = statement.where(AdmissionRequirement.rule_version == rule_set_version)
    requirements = list(session.scalars(statement))
    if not requirements:
        raise RuleSetNotFoundError(
            f"No published admission requirements for program {program_id} "
            f"in {profile.evaluation_year}"
        )
    requirement_ids = {item.id for item in requirements}
    subject_rows = list(
        session.execute(
            select(AdmissionRequirementSubject, Subject)
            .join(Subject, Subject.id == AdmissionRequirementSubject.subject_id)
            .where(AdmissionRequirementSubject.requirement_id.in_(requirement_ids))
        )
    )
    subjects: dict[UUID, list[tuple[str, Decimal | None]]] = {}
    for requirement_subject, subject in subject_rows:
        subjects.setdefault(requirement_subject.requirement_id, []).append(
            (subject.code, requirement_subject.minimum_marks)
        )
    category_codes = _codes_by_id(session, Category, (item.category_id for item in requirements))
    board_codes = _codes_by_id(session, Board, (item.board_id for item in requirements))
    exam_codes = _codes_by_id(session, Exam, (item.exam_id for item in requirements))
    domicile_codes = _codes_by_id(session, State, (item.domicile_state_id for item in requirements))
    gender_codes = _codes_by_id(session, GenderPool, (item.gender_pool_id for item in requirements))
    quota_codes = _codes_by_id(session, QuotaType, (item.quota_type_id for item in requirements))
    rules: list[RuleDefinition] = []
    for requirement in requirements:
        category_code = (
            category_codes.get(requirement.category_id) if requirement.category_id else None
        )
        if category_code is not None and profile.category_code not in {None, category_code}:
            continue
        scope = RuleScope(
            evaluation_year=profile.evaluation_year,
            subject_type=EligibilitySubjectType.PROGRAM,
            subject_id=program.id,
            institution_id=requirement.institution_id,
            program_id=requirement.program_id,
            category_code=category_code,
        )
        evidence = _evidence(
            session,
            source_version_id=requirement.source_document_version_id,
            applicable_year=requirement.academic_year,
            rule_version=requirement.rule_version,
            source_locator=requirement.source_locator,
        )
        if requirement.minimum_marks is not None:
            rules.append(
                _rule(
                    requirement=requirement,
                    suffix="minimum_marks",
                    operator=RuleOperator.MINIMUM,
                    field_name="class12_percentage",
                    expected=requirement.minimum_marks,
                    description=f"Class 12 percentage must be at least {requirement.minimum_marks}",
                    reasons=(
                        ReasonCode.PASS_MINIMUM_MARKS,
                        ReasonCode.FAIL_MINIMUM_MARKS,
                        ReasonCode.MISSING_CLASS12_PERCENTAGE,
                    ),
                    scope=scope,
                    evidence=evidence,
                )
            )
        if requirement.exam_id is not None:
            exam_code = exam_codes[requirement.exam_id]
            rules.append(
                _rule(
                    requirement=requirement,
                    suffix="qualifying_exam",
                    operator=RuleOperator.EQUALS,
                    field_name="exam_code",
                    expected=exam_code,
                    description=f"Qualifying exam must be {exam_code}",
                    reasons=(
                        ReasonCode.PASS_QUALIFYING_EXAM,
                        ReasonCode.FAIL_QUALIFYING_EXAM,
                        ReasonCode.MISSING_QUALIFYING_EXAM,
                    ),
                    scope=scope,
                    evidence=evidence,
                )
            )
        if requirement.board_id is not None:
            board_code = board_codes[requirement.board_id]
            rules.append(
                _rule(
                    requirement=requirement,
                    suffix="board",
                    operator=RuleOperator.EQUALS,
                    field_name="board_code",
                    expected=board_code,
                    description=f"Board must be recognized as {board_code}",
                    reasons=(
                        ReasonCode.PASS_BOARD,
                        ReasonCode.FAIL_BOARD,
                        ReasonCode.MISSING_BOARD,
                    ),
                    scope=scope,
                    evidence=evidence,
                )
            )
        required_subjects = tuple(code for code, _ in subjects.get(requirement.id, []))
        if required_subjects:
            rules.append(
                _rule(
                    requirement=requirement,
                    suffix="required_subjects",
                    operator=RuleOperator.REQUIRED_VALUES,
                    field_name="subjects_studied",
                    expected=required_subjects,
                    description=f"Required subjects: {', '.join(sorted(required_subjects))}",
                    reasons=(
                        ReasonCode.PASS_REQUIRED_SUBJECTS,
                        ReasonCode.FAIL_REQUIRED_SUBJECTS,
                        ReasonCode.MISSING_SUBJECTS,
                    ),
                    scope=scope,
                    evidence=evidence,
                )
            )
        subject_minimums = {
            code: minimum
            for code, minimum in subjects.get(requirement.id, [])
            if minimum is not None
        }
        if subject_minimums:
            rules.append(
                _rule(
                    requirement=requirement,
                    suffix="subject_marks",
                    operator=RuleOperator.SUBJECT_MINIMUMS,
                    field_name="subject_marks",
                    expected=subject_minimums,
                    description="Required subject-specific minimum marks must be satisfied",
                    reasons=(
                        ReasonCode.PASS_SUBJECT_MARKS,
                        ReasonCode.FAIL_SUBJECT_MARKS,
                        ReasonCode.MISSING_SUBJECT_MARKS,
                    ),
                    scope=scope,
                    evidence=evidence,
                )
            )
        optional_rules = (
            (
                requirement.domicile_state_id,
                domicile_codes,
                "domicile",
                "domicile_state_code",
                ReasonCode.PASS_DOMICILE,
                ReasonCode.FAIL_DOMICILE,
                ReasonCode.MISSING_DOMICILE,
            ),
            (
                requirement.gender_pool_id,
                gender_codes,
                "gender",
                "gender_pool_code",
                ReasonCode.PASS_GENDER,
                ReasonCode.FAIL_GENDER,
                ReasonCode.MISSING_GENDER,
            ),
            (
                requirement.quota_type_id,
                quota_codes,
                "quota",
                "quota_code",
                ReasonCode.PASS_CATEGORY,
                ReasonCode.FAIL_CATEGORY,
                ReasonCode.MISSING_CATEGORY,
            ),
        )
        for identifier, codes, suffix, field_name, passed, failed, missing in optional_rules:
            if identifier is not None:
                expected = codes[identifier]
                rules.append(
                    _rule(
                        requirement=requirement,
                        suffix=suffix,
                        operator=RuleOperator.EQUALS,
                        field_name=field_name,
                        expected=expected,
                        description=f"{field_name.replace('_', ' ')} must be {expected}",
                        reasons=(passed, failed, missing),
                        scope=scope,
                        evidence=evidence,
                    )
                )
        scalar_rules: tuple[
            tuple[
                object | None,
                str,
                RuleOperator,
                str,
                tuple[ReasonCode, ReasonCode, ReasonCode],
            ],
            ...,
        ] = (
            (
                requirement.minimum_exam_score,
                "minimum_exam_score",
                RuleOperator.MINIMUM,
                "exam_score",
                (ReasonCode.PASS_SCORE, ReasonCode.FAIL_SCORE, ReasonCode.MISSING_SCORE),
            ),
            (
                requirement.maximum_exam_rank,
                "maximum_exam_rank",
                RuleOperator.MAXIMUM,
                "exam_rank",
                (ReasonCode.PASS_RANK, ReasonCode.FAIL_RANK, ReasonCode.MISSING_RANK),
            ),
            (
                requirement.minimum_age,
                "minimum_age",
                RuleOperator.MINIMUM_AGE,
                "date_of_birth",
                (ReasonCode.PASS_AGE, ReasonCode.FAIL_AGE, ReasonCode.MISSING_DATE_OF_BIRTH),
            ),
            (
                requirement.maximum_age,
                "maximum_age",
                RuleOperator.MAXIMUM_AGE,
                "date_of_birth",
                (ReasonCode.PASS_AGE, ReasonCode.FAIL_AGE, ReasonCode.MISSING_DATE_OF_BIRTH),
            ),
        )
        for scalar_expected, suffix, operator, field_name, reasons in scalar_rules:
            if scalar_expected is not None:
                rules.append(
                    _rule(
                        requirement=requirement,
                        suffix=suffix,
                        operator=operator,
                        field_name=field_name,
                        expected=scalar_expected,
                        description=f"{field_name.replace('_', ' ')} requirement",
                        reasons=reasons,
                        scope=scope,
                        evidence=evidence,
                    )
                )
        boolean_rules: tuple[tuple[bool | None, str, str], ...] = (
            (requirement.required_pwd, "pwd", "is_pwd"),
            (requirement.required_ews, "ews", "is_ews"),
        )
        for boolean_expected, suffix, field_name in boolean_rules:
            if boolean_expected is not None:
                rules.append(
                    _rule(
                        requirement=requirement,
                        suffix=suffix,
                        operator=RuleOperator.BOOLEAN_EQUALS,
                        field_name=field_name,
                        expected=boolean_expected,
                        description=(f"{field_name.replace('_', ' ')} must be {boolean_expected}"),
                        reasons=(
                            ReasonCode.PASS_BOOLEAN_FLAG,
                            ReasonCode.FAIL_BOOLEAN_FLAG,
                            ReasonCode.MISSING_BOOLEAN_FLAG,
                        ),
                        scope=scope,
                        evidence=evidence,
                    )
                )
        if requirement.nationality_code is not None:
            rules.append(
                _rule(
                    requirement=requirement,
                    suffix="nationality",
                    operator=RuleOperator.EQUALS,
                    field_name="nationality_code",
                    expected=requirement.nationality_code,
                    description=f"Nationality must be {requirement.nationality_code}",
                    reasons=(
                        ReasonCode.PASS_CATEGORY,
                        ReasonCode.FAIL_CATEGORY,
                        ReasonCode.MISSING_CATEGORY,
                    ),
                    scope=scope,
                    evidence=evidence,
                )
            )
    if profile.category_code is None:
        scoped_keys = {rule.key for rule in rules if rule.scope.category_code is not None}
        rules = [rule for rule in rules if rule.key not in scoped_keys]
        if scoped_keys:
            first = requirements[0]
            evidence = _evidence(
                session,
                source_version_id=first.source_document_version_id,
                applicable_year=first.academic_year,
                rule_version=first.rule_version,
                source_locator=first.source_locator,
            )
            rules.append(
                RuleDefinition(
                    rule_id="admission:category_for_relaxation",
                    version=first.rule_version,
                    key="admission:category_for_relaxation",
                    operator=RuleOperator.ALLOWED_VALUES,
                    field_name="category_code",
                    expected=tuple(sorted(set(category_codes.values()))),
                    description="Category is required to resolve applicable admission relaxation",
                    pass_reason=ReasonCode.PASS_CATEGORY,
                    fail_reason=ReasonCode.FAIL_CATEGORY,
                    missing_reason=ReasonCode.MISSING_CATEGORY,
                    scope=RuleScope(
                        evaluation_year=profile.evaluation_year,
                        subject_type=EligibilitySubjectType.PROGRAM,
                        subject_id=program.id,
                    ),
                    evidence=evidence,
                )
            )
    versions = sorted({rule.version for rule in rules})
    if not rules:
        raise RuleSetNotFoundError("No applicable program rules after scope resolution")
    candidate = CandidateContext(
        subject_type=EligibilitySubjectType.PROGRAM,
        subject_id=program.id,
        evaluation_year=profile.evaluation_year,
        exam_code=profile.exam_code,
        institution_id=program.institution_id,
        program_id=program.id,
        quota_code=profile.quota_code,
    )
    links = _official_links(
        session,
        [
            (ResourceEntityType.PROGRAM, program.id),
            (ResourceEntityType.INSTITUTION, program.institution_id),
            *(
                (ResourceEntityType.COUNSELLING_AUTHORITY, authority_id)
                for authority_id in session.scalars(
                    select(AdmissionCycle.authority_id).where(
                        AdmissionCycle.academic_year == profile.evaluation_year,
                        AdmissionCycle.exam_id.in_(
                            requirement.exam_id
                            for requirement in requirements
                            if requirement.exam_id is not None
                        ),
                    )
                )
            ),
        ],
        profile.evaluation_year,
    )
    return candidate, RuleSet(version="|".join(versions), rules=tuple(rules)), links


def load_scholarship_rule_set(
    session: Session,
    *,
    profile: StudentEligibilityInput,
    cycle_id: UUID,
) -> tuple[CandidateContext, RuleSet, list[ResourceLink]]:
    cycle = session.get(ScholarshipCycle, cycle_id)
    if cycle is None or cycle.academic_year != profile.evaluation_year:
        raise RuleSetNotFoundError(
            f"Scholarship cycle not found for {profile.evaluation_year}: {cycle_id}"
        )
    scheme = session.get(ScholarshipScheme, cycle.scheme_id)
    rule = session.scalar(
        select(ScholarshipEligibilityRule).where(ScholarshipEligibilityRule.cycle_id == cycle.id)
    )
    if scheme is None or rule is None:
        raise RuleSetNotFoundError(f"Scholarship rule data is incomplete: {cycle_id}")
    evidence = _evidence(
        session,
        source_version_id=cycle.source_document_version_id,
        applicable_year=cycle.academic_year,
        rule_version=cycle.rule_version,
        source_locator=rule.source_locator,
    )
    scope = RuleScope(
        evaluation_year=profile.evaluation_year,
        subject_type=EligibilitySubjectType.SCHOLARSHIP,
        subject_id=scheme.id,
        scholarship_id=scheme.id,
    )
    rules: list[RuleDefinition] = []

    def add_rule(
        suffix: str,
        operator: RuleOperator,
        field_name: str,
        expected: object,
        description: str,
        reasons: tuple[ReasonCode, ReasonCode, ReasonCode],
    ) -> None:
        rules.append(
            RuleDefinition(
                rule_id=f"{scheme.official_code}:{suffix}",
                version=cycle.rule_version,
                key=f"{scheme.official_code}:{suffix}",
                operator=operator,
                field_name=field_name,
                expected=expected,
                description=description,
                pass_reason=reasons[0],
                fail_reason=reasons[1],
                missing_reason=reasons[2],
                scope=scope,
                evidence=evidence,
            )
        )

    if rule.income_max is not None:
        add_rule(
            "income_max",
            RuleOperator.MAXIMUM,
            "family_income",
            rule.income_max,
            f"Family income must not exceed {rule.income_max}",
            (
                ReasonCode.PASS_INCOME_LIMIT,
                ReasonCode.FAIL_INCOME_LIMIT,
                ReasonCode.MISSING_FAMILY_INCOME,
            ),
        )
    if rule.minimum_marks is not None:
        add_rule(
            "minimum_marks",
            RuleOperator.MINIMUM,
            "class12_percentage",
            rule.minimum_marks,
            f"Class 12 percentage must be at least {rule.minimum_marks}",
            (
                ReasonCode.PASS_MINIMUM_MARKS,
                ReasonCode.FAIL_MINIMUM_MARKS,
                ReasonCode.MISSING_CLASS12_PERCENTAGE,
            ),
        )
    if rule.achievement_code is not None and rule.achievement_minimum is not None:
        add_rule(
            "achievement",
            RuleOperator.ACHIEVEMENT_MINIMUM,
            "achievements",
            (rule.achievement_code, rule.achievement_minimum),
            f"Achievement {rule.achievement_code} must meet the published minimum",
            (
                ReasonCode.PASS_ACHIEVEMENT,
                ReasonCode.FAIL_ACHIEVEMENT,
                ReasonCode.MISSING_ACHIEVEMENT,
            ),
        )
    association_rules: tuple[
        tuple[Any, Any, Any, str, str, ReasonCode, ReasonCode, ReasonCode], ...
    ] = (
        (
            ScholarshipEligibleCategory,
            ScholarshipEligibleCategory.category_id,
            Category,
            "category",
            "category_code",
            ReasonCode.PASS_CATEGORY,
            ReasonCode.FAIL_CATEGORY,
            ReasonCode.MISSING_CATEGORY,
        ),
        (
            ScholarshipEligibleState,
            ScholarshipEligibleState.state_id,
            State,
            "state",
            "domicile_state_code",
            ReasonCode.PASS_DOMICILE,
            ReasonCode.FAIL_DOMICILE,
            ReasonCode.MISSING_DOMICILE,
        ),
        (
            ScholarshipEligibleGenderPool,
            ScholarshipEligibleGenderPool.gender_pool_id,
            GenderPool,
            "gender",
            "gender_pool_code",
            ReasonCode.PASS_GENDER,
            ReasonCode.FAIL_GENDER,
            ReasonCode.MISSING_GENDER,
        ),
        (
            ScholarshipEligibleInstitutionType,
            ScholarshipEligibleInstitutionType.institution_type_id,
            InstitutionType,
            "institution_type",
            "institution_type_code",
            ReasonCode.PASS_INSTITUTION_TYPE,
            ReasonCode.FAIL_INSTITUTION_TYPE,
            ReasonCode.MISSING_INSTITUTION_TYPE,
        ),
    )
    for (
        association,
        id_column,
        vocabulary,
        suffix,
        field_name,
        passed,
        failed,
        missing,
    ) in association_rules:
        vocabulary_ids = list(
            session.scalars(select(id_column).where(association.__table__.c.cycle_id == cycle.id))
        )
        if vocabulary_ids:
            codes = _codes_by_id(session, vocabulary, vocabulary_ids)
            add_rule(
                suffix,
                RuleOperator.ALLOWED_VALUES,
                field_name,
                tuple(sorted(codes.values())),
                f"{field_name.replace('_', ' ')} must be permitted by the scheme",
                (passed, failed, missing),
            )
    program_ids = list(
        session.scalars(
            select(ScholarshipEligibleProgram.program_id).where(
                ScholarshipEligibleProgram.cycle_id == cycle.id
            )
        )
    )
    if program_ids:
        add_rule(
            "program",
            RuleOperator.ALLOWED_VALUES,
            "target_program_id",
            tuple(program_ids),
            "Target program must be permitted by the scheme",
            (ReasonCode.PASS_COURSE, ReasonCode.FAIL_COURSE, ReasonCode.MISSING_COURSE),
        )
    required_documents = list(
        session.scalars(
            select(ScholarshipRequiredDocument).where(
                ScholarshipRequiredDocument.cycle_id == cycle.id,
                ScholarshipRequiredDocument.is_required.is_(True),
            )
        )
    )
    for document in required_documents:
        add_rule(
            f"credential:{document.document_code}",
            RuleOperator.REQUIRED_CREDENTIAL,
            "credentials",
            document.document_code,
            f"Credential {document.name} is required",
            (
                ReasonCode.PASS_CREDENTIAL,
                ReasonCode.FAIL_CREDENTIAL,
                ReasonCode.MISSING_CREDENTIAL,
            ),
        )
    candidate = CandidateContext(
        subject_type=EligibilitySubjectType.SCHOLARSHIP,
        subject_id=scheme.id,
        evaluation_year=profile.evaluation_year,
        scholarship_id=scheme.id,
        program_id=profile.target_program_id,
    )
    links = _official_links(
        session,
        ((ResourceEntityType.SCHOLARSHIP, scheme.id),),
        profile.evaluation_year,
    )
    return (
        candidate,
        RuleSet(version=cycle.rule_version, rules=tuple(rules)),
        links,
    )
