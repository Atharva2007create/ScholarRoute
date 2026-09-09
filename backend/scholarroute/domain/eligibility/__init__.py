"""Deterministic, auditable eligibility evaluation."""

from scholarroute.domain.eligibility.engine import evaluate_eligibility
from scholarroute.domain.eligibility.models import (
    CandidateContext,
    EligibilityDecision,
    EligibilityStatus,
    EligibilitySubjectType,
    ReasonCode,
    RuleDefinition,
    RuleEvidence,
    RuleGroup,
    RuleOperator,
    RuleScope,
    RuleSet,
    StudentEligibilityInput,
)

__all__ = [
    "CandidateContext",
    "EligibilityDecision",
    "EligibilityStatus",
    "EligibilitySubjectType",
    "ReasonCode",
    "RuleDefinition",
    "RuleEvidence",
    "RuleGroup",
    "RuleOperator",
    "RuleScope",
    "RuleSet",
    "StudentEligibilityInput",
    "evaluate_eligibility",
]
