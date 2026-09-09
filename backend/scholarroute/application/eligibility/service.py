from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from scholarroute.application.eligibility.repository import (
    load_program_rule_set,
    load_scholarship_rule_set,
    validate_student_references,
)
from scholarroute.domain.eligibility.engine import evaluate_eligibility
from scholarroute.domain.eligibility.models import (
    EligibilityDecision,
    RuleEvaluation,
    RuleSet,
    StudentEligibilityInput,
)
from scholarroute.infrastructure.db.models import (
    EligibilityEvaluation,
    EligibilityEvaluationResourceLink,
    EligibilityInputSnapshot,
    EligibilityRuleResult,
    ResourceLink,
)
from scholarroute.infrastructure.db.models.enums import (
    EligibilityStatus as DatabaseEligibilityStatus,
)
from scholarroute.infrastructure.db.models.enums import (
    EligibilitySubjectType as DatabaseEligibilitySubjectType,
)
from scholarroute.infrastructure.db.models.enums import (
    RuleEvaluationStatus as DatabaseRuleEvaluationStatus,
)


@dataclass(frozen=True)
class EligibilityResult:
    evaluation_id: UUID
    decision: EligibilityDecision
    official_links: tuple[str, ...]


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (UUID, Decimal, date, datetime)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (set, frozenset, tuple, list)):
        converted = [_json_value(item) for item in value]
        return sorted(converted, key=str) if isinstance(value, (set, frozenset)) else converted
    return value


def _rules_hash(rule_set: RuleSet) -> str:
    payload = json.dumps(_json_value(asdict(rule_set)), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class EligibilityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def evaluate_program(
        self,
        *,
        profile: StudentEligibilityInput,
        program_id: UUID,
        rule_set_version: str | None = None,
        evaluated_at: datetime | None = None,
    ) -> EligibilityResult:
        validate_student_references(self.session, profile)
        candidate, rule_set, links = load_program_rule_set(
            self.session,
            profile=profile,
            program_id=program_id,
            rule_set_version=rule_set_version,
        )
        decision = evaluate_eligibility(
            profile=profile,
            candidate=candidate,
            rule_set=rule_set,
            evaluated_at=evaluated_at or datetime.now(UTC),
        )
        return self._persist(profile, rule_set, decision, links)

    def evaluate_scholarship(
        self,
        *,
        profile: StudentEligibilityInput,
        cycle_id: UUID,
        evaluated_at: datetime | None = None,
    ) -> EligibilityResult:
        validate_student_references(self.session, profile)
        candidate, rule_set, links = load_scholarship_rule_set(
            self.session,
            profile=profile,
            cycle_id=cycle_id,
        )
        decision = evaluate_eligibility(
            profile=profile,
            candidate=candidate,
            rule_set=rule_set,
            evaluated_at=evaluated_at or datetime.now(UTC),
        )
        return self._persist(profile, rule_set, decision, links)

    def _persist(
        self,
        profile: StudentEligibilityInput,
        rule_set: RuleSet,
        decision: EligibilityDecision,
        links: list[ResourceLink],
    ) -> EligibilityResult:
        snapshot = EligibilityInputSnapshot(
            profile_identifier=profile.profile_id,
            schema_version=profile.snapshot_version,
            evaluation_year=profile.evaluation_year,
            input_hash=profile.content_hash(),
            normalized_input=profile.canonical_payload(),
        )
        self.session.add(snapshot)
        self.session.flush()
        record = EligibilityEvaluation(
            snapshot_id=snapshot.id,
            subject_type=DatabaseEligibilitySubjectType(decision.subject_type.value),
            subject_id=decision.subject_id,
            evaluation_year=decision.evaluation_year,
            status=DatabaseEligibilityStatus(decision.status.value),
            rule_set_version=decision.rule_set_version,
            catalog_release_id=decision.catalog_release_id,
            rules_hash=_rules_hash(rule_set),
            evaluated_at=decision.evaluated_at,
            reason_codes=[reason.value for reason in decision.reason_codes],
            missing_information=list(decision.missing_information),
            human_summary=decision.human_summary,
        )
        self.session.add(record)
        self.session.flush()
        sequence = 0

        def add_result(item: RuleEvaluation, parent_id: UUID | None = None) -> None:
            nonlocal sequence
            sequence += 1
            evidence = item.evidence
            result = EligibilityRuleResult(
                evaluation_id=record.id,
                parent_result_id=parent_id,
                sequence=sequence,
                rule_id=item.rule_id,
                rule_version=item.rule_version,
                status=DatabaseRuleEvaluationStatus(item.status.value),
                reason_code=item.reason_code.value,
                message=item.message,
                observed_value=_json_value(item.observed_value),
                expected_value=_json_value(item.expected_value),
                source_document_version_id=(
                    evidence.source_document_version_id if evidence else None
                ),
                source_locator=evidence.source_locator if evidence else None,
                official_url=evidence.official_url if evidence else None,
            )
            self.session.add(result)
            self.session.flush()
            for child in item.children:
                add_result(child, result.id)

        for evaluation in decision.evaluations:
            add_result(evaluation)
        for link in links:
            self.session.add(
                EligibilityEvaluationResourceLink(
                    evaluation_id=record.id,
                    resource_link_id=link.id,
                )
            )
        self.session.flush()
        return EligibilityResult(
            evaluation_id=record.id,
            decision=decision,
            official_links=tuple(sorted({link.url for link in links})),
        )
