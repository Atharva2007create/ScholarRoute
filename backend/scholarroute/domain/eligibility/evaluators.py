from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import date
from decimal import Decimal
from typing import Any

from scholarroute.domain.eligibility.models import (
    CandidateContext,
    LogicalOperator,
    ReasonCode,
    RuleDefinition,
    RuleEvaluation,
    RuleGroup,
    RuleNode,
    RuleOperator,
    RuleResultStatus,
    StudentEligibilityInput,
)


def _field_value(profile: StudentEligibilityInput, field_name: str) -> Any:
    if not hasattr(profile, field_name):
        raise ValueError(f"Unsupported eligibility field: {field_name}")
    return getattr(profile, field_name)


def _age_on(birth_date: date, evaluation_date: date) -> int:
    return (
        evaluation_date.year
        - birth_date.year
        - ((evaluation_date.month, evaluation_date.day) < (birth_date.month, birth_date.day))
    )


def _compare(rule: RuleDefinition, observed: Any, profile: StudentEligibilityInput) -> bool:
    if rule.operator is RuleOperator.MINIMUM:
        return bool(observed >= rule.expected)
    if rule.operator is RuleOperator.MAXIMUM:
        return bool(observed <= rule.expected)
    if rule.operator in {RuleOperator.EQUALS, RuleOperator.BOOLEAN_EQUALS}:
        return bool(observed == rule.expected)
    if rule.operator is RuleOperator.ALLOWED_VALUES:
        return observed in rule.expected
    if rule.operator is RuleOperator.EXCLUDED_VALUES:
        return observed not in rule.expected
    if rule.operator is RuleOperator.REQUIRED_VALUES:
        return set(rule.expected).issubset(set(observed))
    if rule.operator is RuleOperator.SUBJECT_MINIMUMS:
        expected: Mapping[str, Decimal] = rule.expected
        return all(observed.get(subject) >= minimum for subject, minimum in expected.items())
    if rule.operator is RuleOperator.REQUIRED_CREDENTIAL:
        return rule.expected in observed
    if rule.operator is RuleOperator.ACHIEVEMENT_MINIMUM:
        code, minimum = rule.expected
        return bool(observed.get(code) is not None and observed[code] >= minimum)
    if rule.operator in {RuleOperator.MINIMUM_AGE, RuleOperator.MAXIMUM_AGE}:
        if profile.evaluation_date is None:
            return False
        age = _age_on(observed, profile.evaluation_date)
        expected_age = int(rule.expected)
        return (
            age >= expected_age
            if rule.operator is RuleOperator.MINIMUM_AGE
            else age <= expected_age
        )
    raise ValueError(f"Unsupported rule operator: {rule.operator}")


def _missing(rule: RuleDefinition, observed: Any, profile: StudentEligibilityInput) -> bool:
    if observed is None:
        return True
    if rule.operator is RuleOperator.SUBJECT_MINIMUMS:
        expected: Collection[str] = rule.expected
        return any(subject not in observed for subject in expected)
    if rule.operator is RuleOperator.ACHIEVEMENT_MINIMUM:
        code, _ = rule.expected
        return observed is None or code not in observed
    return (
        rule.operator in {RuleOperator.MINIMUM_AGE, RuleOperator.MAXIMUM_AGE}
        and profile.evaluation_date is None
    )


def evaluate_rule(rule: RuleDefinition, profile: StudentEligibilityInput) -> RuleEvaluation:
    observed = _field_value(profile, rule.field_name)
    if _missing(rule, observed, profile):
        return RuleEvaluation(
            rule_id=rule.rule_id,
            rule_version=rule.version,
            status=RuleResultStatus.MISSING,
            reason_code=rule.missing_reason,
            message=f"Eligibility needs {rule.field_name.replace('_', ' ')}.",
            observed_value=observed,
            expected_value=rule.expected,
            evidence=rule.evidence,
        )
    passed = _compare(rule, observed, profile)
    return RuleEvaluation(
        rule_id=rule.rule_id,
        rule_version=rule.version,
        status=RuleResultStatus.PASSED if passed else RuleResultStatus.FAILED,
        reason_code=rule.pass_reason if passed else rule.fail_reason,
        message=f"{'Passed' if passed else 'Not eligible'}: {rule.description}.",
        observed_value=observed,
        expected_value=rule.expected,
        evidence=rule.evidence,
    )


def evaluate_group(
    group: RuleGroup,
    profile: StudentEligibilityInput,
    candidate: CandidateContext,
) -> RuleEvaluation:
    children = tuple(evaluate_node(child, profile, candidate) for child in group.children)
    applicable = tuple(
        child for child in children if child.status is not RuleResultStatus.NOT_APPLICABLE
    )
    if not applicable:
        status = RuleResultStatus.NOT_APPLICABLE
        reason = ReasonCode.RULE_NOT_APPLICABLE
    elif group.operator is LogicalOperator.AND:
        if any(child.status is RuleResultStatus.FAILED for child in applicable):
            status, reason = RuleResultStatus.FAILED, ReasonCode.RULE_GROUP_FAILED
        elif any(
            child.status in {RuleResultStatus.MISSING, RuleResultStatus.CONFLICT}
            for child in applicable
        ):
            status, reason = RuleResultStatus.MISSING, ReasonCode.RULE_GROUP_MISSING
        else:
            status, reason = RuleResultStatus.PASSED, ReasonCode.RULE_GROUP_PASSED
    elif any(child.status is RuleResultStatus.PASSED for child in applicable):
        status, reason = RuleResultStatus.PASSED, ReasonCode.RULE_GROUP_PASSED
    elif all(child.status is RuleResultStatus.FAILED for child in applicable):
        status, reason = RuleResultStatus.FAILED, ReasonCode.RULE_GROUP_FAILED
    else:
        status, reason = RuleResultStatus.MISSING, ReasonCode.RULE_GROUP_MISSING
    return RuleEvaluation(
        rule_id=group.rule_id,
        rule_version=group.version,
        status=status,
        reason_code=reason,
        message=f"{status.value.title()}: {group.description}.",
        evidence=group.evidence,
        children=children,
    )


def scope_applies(
    rule: RuleNode,
    profile: StudentEligibilityInput,
    candidate: CandidateContext,
) -> bool:
    scope = rule.scope
    comparisons = (
        (scope.evaluation_year, candidate.evaluation_year),
        (scope.subject_type, candidate.subject_type),
        (scope.subject_id, candidate.subject_id),
        (scope.exam_code, candidate.exam_code),
        (scope.authority_code, candidate.authority_code),
        (scope.institution_id, candidate.institution_id),
        (scope.program_id, candidate.program_id),
        (scope.scholarship_id, candidate.scholarship_id),
        (scope.category_code, profile.category_code),
        (scope.quota_code, candidate.quota_code),
        (scope.domicile_state_code, profile.domicile_state_code),
    )
    return all(expected is None or expected == actual for expected, actual in comparisons)


def evaluate_node(
    node: RuleNode,
    profile: StudentEligibilityInput,
    candidate: CandidateContext,
) -> RuleEvaluation:
    if not scope_applies(node, profile, candidate):
        return RuleEvaluation(
            rule_id=node.rule_id,
            rule_version=node.version,
            status=RuleResultStatus.NOT_APPLICABLE,
            reason_code=ReasonCode.RULE_NOT_APPLICABLE,
            message="Rule is outside the selected subject, year, or scope.",
            evidence=node.evidence,
        )
    if isinstance(node, RuleGroup):
        return evaluate_group(node, profile, candidate)
    return evaluate_rule(node, profile)
