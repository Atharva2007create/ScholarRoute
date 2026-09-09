from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from scholarroute.domain.eligibility.evaluators import evaluate_node, scope_applies
from scholarroute.domain.eligibility.models import (
    CandidateContext,
    EligibilityDecision,
    EligibilityStatus,
    ReasonCode,
    RuleDefinition,
    RuleEvaluation,
    RuleNode,
    RuleResultStatus,
    RuleSet,
    StudentEligibilityInput,
)


def _signature(node: RuleNode) -> str:
    if isinstance(node, RuleDefinition):
        payload: dict[str, Any] = {
            "version": node.version,
            "operator": node.operator,
            "field": node.field_name,
            "expected": node.expected,
        }
    else:
        payload = {
            "version": node.version,
            "operator": node.operator,
            "children": [_signature(child) for child in node.children],
        }
    return json.dumps(payload, sort_keys=True, default=str)


def resolve_rules(
    rules: tuple[RuleNode, ...],
    profile: StudentEligibilityInput,
    candidate: CandidateContext,
) -> tuple[tuple[RuleNode, ...], tuple[RuleEvaluation, ...]]:
    applicable = [rule for rule in rules if scope_applies(rule, profile, candidate)]
    grouped: dict[str, list[RuleNode]] = {}
    for rule in applicable:
        grouped.setdefault(rule.key, []).append(rule)
    selected: list[RuleNode] = []
    conflicts: list[RuleEvaluation] = []
    for key in sorted(grouped):
        candidates = grouped[key]
        highest = max(rule.scope.specificity for rule in candidates)
        winners = [rule for rule in candidates if rule.scope.specificity == highest]
        signatures = {_signature(rule) for rule in winners}
        if len(signatures) > 1:
            first = winners[0]
            conflicts.append(
                RuleEvaluation(
                    rule_id=first.rule_id,
                    rule_version=first.version,
                    status=RuleResultStatus.CONFLICT,
                    reason_code=ReasonCode.RULE_CONFLICT,
                    message=f"Conflicting authoritative rules share scope key {key}.",
                    evidence=first.evidence,
                )
            )
        else:
            selected.append(winners[0])
    return tuple(selected), tuple(conflicts)


def _flatten(evaluation: RuleEvaluation) -> tuple[RuleEvaluation, ...]:
    return (
        evaluation,
        *(descendant for child in evaluation.children for descendant in _flatten(child)),
    )


def evaluate_eligibility(
    *,
    profile: StudentEligibilityInput,
    candidate: CandidateContext,
    rule_set: RuleSet,
    evaluated_at: datetime,
) -> EligibilityDecision:
    if profile.evaluation_year != candidate.evaluation_year:
        raise ValueError("Student evaluation year and candidate year must match")
    selected, conflicts = resolve_rules(rule_set.rules, profile, candidate)
    evaluations = tuple(evaluate_node(rule, profile, candidate) for rule in selected) + conflicts
    flattened = tuple(item for evaluation in evaluations for item in _flatten(evaluation))
    top_level = tuple(
        item for item in evaluations if item.status is not RuleResultStatus.NOT_APPLICABLE
    )
    trace = tuple(item for item in flattened if item.status is not RuleResultStatus.NOT_APPLICABLE)
    reason_codes: tuple[ReasonCode, ...]
    missing: tuple[str, ...]
    if not top_level:
        status = EligibilityStatus.NEEDS_INFORMATION
        reason_codes = (ReasonCode.RULE_NOT_APPLICABLE,)
        missing = ("published eligibility rule",)
        summary = "Eligibility cannot be determined because no applicable published rule exists."
    elif any(item.status is RuleResultStatus.FAILED for item in top_level):
        status = EligibilityStatus.INELIGIBLE
        reason_codes = tuple(dict.fromkeys(item.reason_code for item in trace))
        missing = ()
        count = sum(item.status is RuleResultStatus.FAILED for item in top_level)
        summary = f"Ineligible because {count} mandatory eligibility rule(s) failed."
    elif any(
        item.status in {RuleResultStatus.MISSING, RuleResultStatus.CONFLICT} for item in top_level
    ):
        status = EligibilityStatus.NEEDS_INFORMATION
        reason_codes = tuple(dict.fromkeys(item.reason_code for item in trace))
        missing = tuple(
            dict.fromkeys(
                item.message
                for item in top_level
                if item.status in {RuleResultStatus.MISSING, RuleResultStatus.CONFLICT}
            )
        )
        summary = (
            "Eligibility cannot be determined because required information is "
            "missing or conflicting."
        )
    else:
        status = EligibilityStatus.ELIGIBLE
        reason_codes = tuple(dict.fromkeys(item.reason_code for item in trace))
        missing = ()
        summary = f"Eligible because all {len(top_level)} applicable eligibility rule(s) passed."
    return EligibilityDecision(
        status=status,
        subject_type=candidate.subject_type,
        subject_id=candidate.subject_id,
        evaluation_year=candidate.evaluation_year,
        student_snapshot_hash=profile.content_hash(),
        rule_set_version=rule_set.version,
        evaluated_at=evaluated_at,
        evaluations=evaluations,
        reason_codes=reason_codes,
        missing_information=missing,
        human_summary=summary,
        catalog_release_id=rule_set.catalog_release_id,
    )
