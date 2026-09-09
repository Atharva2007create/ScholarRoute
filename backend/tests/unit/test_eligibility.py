from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from scholarroute.domain.eligibility.engine import evaluate_eligibility
from scholarroute.domain.eligibility.models import (
    CandidateContext,
    EligibilityStatus,
    EligibilitySubjectType,
    LogicalOperator,
    ReasonCode,
    RuleDefinition,
    RuleEvidence,
    RuleGroup,
    RuleOperator,
    RuleResultStatus,
    RuleScope,
    RuleSet,
    StudentEligibilityInput,
)

NOW = datetime(2026, 9, 9, tzinfo=UTC)
SUBJECT_ID = UUID("10000000-0000-0000-0000-000000000001")


def evidence(version: str = "2026.1") -> RuleEvidence:
    return RuleEvidence(
        source_document_version_id=uuid4(),
        source_authority="Official authority",
        source_document="Published rules",
        source_locator="page 4",
        official_url="https://official.example/rules",
        applicable_year=2026,
        rule_version=version,
        verified_at=NOW,
    )


def rule(
    *,
    operator: RuleOperator = RuleOperator.MINIMUM,
    field_name: str = "class12_percentage",
    expected: object = Decimal("60"),
    key: str = "marks",
    version: str = "2026.1",
    scope: RuleScope | None = None,
) -> RuleDefinition:
    return RuleDefinition(
        rule_id=f"rule:{key}:{version}",
        version=version,
        key=key,
        operator=operator,
        field_name=field_name,
        expected=expected,
        description="published requirement",
        pass_reason=ReasonCode.PASS_MINIMUM_MARKS,
        fail_reason=ReasonCode.FAIL_MINIMUM_MARKS,
        missing_reason=ReasonCode.MISSING_CLASS12_PERCENTAGE,
        scope=scope
        or RuleScope(
            evaluation_year=2026,
            subject_type=EligibilitySubjectType.PROGRAM,
            subject_id=SUBJECT_ID,
        ),
        evidence=evidence(version),
    )


def decide(profile: StudentEligibilityInput, *rules: RuleDefinition | RuleGroup):
    return evaluate_eligibility(
        profile=profile,
        candidate=CandidateContext(
            subject_type=EligibilitySubjectType.PROGRAM,
            subject_id=SUBJECT_ID,
            evaluation_year=2026,
            program_id=SUBJECT_ID,
        ),
        rule_set=RuleSet(version="2026.1", rules=rules),
        evaluated_at=NOW,
    )


def test_three_state_decision_and_normalized_snapshot_are_deterministic() -> None:
    eligible = StudentEligibilityInput(evaluation_year=2026, class12_percentage=65)
    ineligible = StudentEligibilityInput(evaluation_year=2026, class12_percentage=55)
    incomplete = StudentEligibilityInput(evaluation_year=2026)

    assert decide(eligible, rule()).status is EligibilityStatus.ELIGIBLE
    assert decide(ineligible, rule()).status is EligibilityStatus.INELIGIBLE
    missing = decide(incomplete, rule())
    assert missing.status is EligibilityStatus.NEEDS_INFORMATION
    assert missing.reason_codes == (ReasonCode.MISSING_CLASS12_PERCENTAGE,)
    assert eligible.content_hash() == eligible.model_copy().content_hash()


def test_and_or_groups_use_group_result_for_final_decision() -> None:
    profile = StudentEligibilityInput(evaluation_year=2026, class12_percentage=65, exam_rank=20)
    passing = rule()
    failing = rule(
        operator=RuleOperator.MAXIMUM,
        field_name="exam_rank",
        expected=10,
        key="rank",
    )
    scope = passing.scope
    or_group = RuleGroup(
        rule_id="group:or",
        version="2026.1",
        key="route",
        operator=LogicalOperator.OR,
        children=(passing, failing),
        description="either route",
        scope=scope,
        evidence=evidence(),
    )
    and_group = RuleGroup(
        rule_id="group:and",
        version="2026.1",
        key="all",
        operator=LogicalOperator.AND,
        children=(passing, failing),
        description="all requirements",
        scope=scope,
        evidence=evidence(),
    )

    assert decide(profile, or_group).status is EligibilityStatus.ELIGIBLE
    assert decide(profile, and_group).status is EligibilityStatus.INELIGIBLE


def test_specific_scope_overrides_general_and_equal_scope_conflicts_are_safe() -> None:
    profile = StudentEligibilityInput(evaluation_year=2026, class12_percentage=57)
    general = rule(expected=Decimal("60"))
    program_specific = rule(
        expected=Decimal("55"),
        scope=RuleScope(
            evaluation_year=2026,
            subject_type=EligibilitySubjectType.PROGRAM,
            subject_id=SUBJECT_ID,
            program_id=SUBJECT_ID,
        ),
    )
    assert decide(profile, general, program_specific).status is EligibilityStatus.ELIGIBLE

    conflict = rule(expected=Decimal("70"), version="2026.2", scope=program_specific.scope)
    result = decide(profile, program_specific, conflict)
    assert result.status is EligibilityStatus.NEEDS_INFORMATION
    assert ReasonCode.RULE_CONFLICT in result.reason_codes


@pytest.mark.parametrize(
    ("operator", "field_name", "expected", "value", "status"),
    [
        (RuleOperator.EQUALS, "board_code", "CBSE", "cbse", EligibilityStatus.ELIGIBLE),
        (
            RuleOperator.ALLOWED_VALUES,
            "category_code",
            ("SC", "ST"),
            "OBC",
            EligibilityStatus.INELIGIBLE,
        ),
        (
            RuleOperator.EQUALS,
            "domicile_state_code",
            "MH",
            "DL",
            EligibilityStatus.INELIGIBLE,
        ),
        (
            RuleOperator.ALLOWED_VALUES,
            "gender_pool_code",
            ("FEMALE_ONLY",),
            "female only",
            EligibilityStatus.ELIGIBLE,
        ),
        (
            RuleOperator.ALLOWED_VALUES,
            "target_program_id",
            (SUBJECT_ID,),
            SUBJECT_ID,
            EligibilityStatus.ELIGIBLE,
        ),
        (
            RuleOperator.REQUIRED_VALUES,
            "subjects_studied",
            ("PHYSICS", "MATHS"),
            {"physics", "maths"},
            EligibilityStatus.ELIGIBLE,
        ),
        (
            RuleOperator.SUBJECT_MINIMUMS,
            "subject_marks",
            {"MATHS": Decimal("60")},
            {"maths": 59},
            EligibilityStatus.INELIGIBLE,
        ),
        (
            RuleOperator.REQUIRED_CREDENTIAL,
            "credentials",
            "INCOME_CERTIFICATE",
            {"income_certificate"},
            EligibilityStatus.ELIGIBLE,
        ),
        (
            RuleOperator.ACHIEVEMENT_MINIMUM,
            "achievements",
            ("SPORT_LEVEL", Decimal("2")),
            {"sport_level": 3},
            EligibilityStatus.ELIGIBLE,
        ),
    ],
)
def test_typed_rule_operators(
    operator: RuleOperator,
    field_name: str,
    expected: object,
    value: object,
    status: EligibilityStatus,
) -> None:
    profile = StudentEligibilityInput(evaluation_year=2026, **{field_name: value})
    result = decide(
        profile,
        rule(operator=operator, field_name=field_name, expected=expected),
    )
    assert result.status is status


def test_age_rule_uses_explicit_evaluation_date() -> None:
    profile = StudentEligibilityInput(
        evaluation_year=2026,
        evaluation_date=date(2026, 12, 31),
        date_of_birth=date(2009, 1, 1),
    )
    age_rule = rule(
        operator=RuleOperator.MINIMUM_AGE,
        field_name="date_of_birth",
        expected=17,
    )
    assert decide(profile, age_rule).status is EligibilityStatus.ELIGIBLE


def test_category_specific_relaxation_overrides_general_threshold() -> None:
    profile = StudentEligibilityInput(
        evaluation_year=2026,
        category_code="SC",
        class12_percentage=Decimal("57"),
    )
    general = rule(expected=Decimal("60"))
    relaxation = rule(
        expected=Decimal("55"),
        scope=RuleScope(
            evaluation_year=2026,
            subject_type=EligibilitySubjectType.PROGRAM,
            subject_id=SUBJECT_ID,
            category_code="SC",
        ),
    )
    assert decide(profile, general, relaxation).status is EligibilityStatus.ELIGIBLE


def test_multiple_failures_are_preserved_in_trace() -> None:
    profile = StudentEligibilityInput(
        evaluation_year=2026,
        class12_percentage=Decimal("50"),
        exam_rank=100,
    )
    result = decide(
        profile,
        rule(),
        rule(
            operator=RuleOperator.MAXIMUM,
            field_name="exam_rank",
            expected=10,
            key="rank",
        ),
    )
    assert result.status is EligibilityStatus.INELIGIBLE
    assert sum(item.status is RuleResultStatus.FAILED for item in result.evaluations) == 2


def test_invalid_input_is_rejected_before_evaluation() -> None:
    with pytest.raises(ValidationError):
        StudentEligibilityInput(evaluation_year=2026, exam_rank=0)
    with pytest.raises(ValidationError):
        StudentEligibilityInput(evaluation_year=2026, subject_marks={"MATHS": 101})
    with pytest.raises(ValidationError):
        StudentEligibilityInput(evaluation_year=2026, board_code="!!!")


def test_historical_cutoff_is_not_an_eligibility_input() -> None:
    fields = StudentEligibilityInput.model_fields
    assert "historical_cutoff" not in fields
    assert "opening_rank" not in fields
    assert "closing_rank" not in fields


def test_non_applicable_rules_do_not_produce_false_eligibility() -> None:
    other_subject = uuid4()
    outside_scope = rule(
        scope=RuleScope(
            evaluation_year=2026,
            subject_type=EligibilitySubjectType.PROGRAM,
            subject_id=other_subject,
        )
    )
    result = decide(
        StudentEligibilityInput(evaluation_year=2026, class12_percentage=90), outside_scope
    )
    assert result.status is EligibilityStatus.NEEDS_INFORMATION
    assert result.evaluations == ()


def test_or_group_missing_plus_failure_needs_information() -> None:
    profile = StudentEligibilityInput(evaluation_year=2026, exam_rank=50)
    missing = rule()
    failed = rule(
        operator=RuleOperator.MAXIMUM,
        field_name="exam_rank",
        expected=10,
        key="rank",
    )
    group = RuleGroup(
        rule_id="group:or",
        version="2026.1",
        key="route",
        operator=LogicalOperator.OR,
        children=(missing, failed),
        description="either route",
        scope=missing.scope,
        evidence=evidence(),
    )
    evaluation = decide(profile, group)
    assert evaluation.status is EligibilityStatus.NEEDS_INFORMATION
    assert evaluation.evaluations[0].status is RuleResultStatus.MISSING
