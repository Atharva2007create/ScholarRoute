from datetime import UTC, datetime

from fastapi import APIRouter

from scholarroute.application.eligibility.repository import (
    InvalidStudentReferenceError,
    RuleSetNotFoundError,
)
from scholarroute.application.eligibility.service import EligibilityResult, EligibilityService
from scholarroute.domain.eligibility.models import EligibilitySubjectType
from scholarroute.entrypoints.api.dependencies import SessionDependency
from scholarroute.entrypoints.api.v1.schemas import (
    EligibilityRequest,
    EligibilityResponse,
    EvidenceResponse,
    RuleResponse,
)
from scholarroute.errors import ApplicationError

router = APIRouter(prefix="/api/v1/eligibility", tags=["Eligibility"])


def map_eligibility(result: EligibilityResult) -> EligibilityResponse:
    decision = result.decision
    return EligibilityResponse(
        evaluation_id=result.evaluation_id,
        subject_type=decision.subject_type.value,
        subject_id=decision.subject_id,
        status=decision.status.value,
        reason_codes=[item.value for item in decision.reason_codes],
        missing_information=list(decision.missing_information),
        summary=decision.human_summary,
        rule_set_version=decision.rule_set_version,
        evaluated_at=decision.evaluated_at,
        rules=[
            RuleResponse(
                rule_id=item.rule_id,
                status=item.status.value,
                reason_code=item.reason_code.value,
                message=item.message,
                evidence=EvidenceResponse(
                    source_document_version_id=item.evidence.source_document_version_id,
                    source_locator=item.evidence.source_locator,
                    official_url=item.evidence.official_url,
                    applicable_year=item.evidence.applicable_year,
                    rule_version=item.evidence.rule_version,
                )
                if item.evidence
                else None,
            )
            for item in decision.evaluations
        ],
        official_links=list(result.official_links),
    )


@router.post(
    "/evaluate", response_model=EligibilityResponse, summary="Evaluate published eligibility rules"
)
def evaluate(request: EligibilityRequest, session: SessionDependency) -> EligibilityResponse:
    service = EligibilityService(session)
    try:
        if request.subject_type is EligibilitySubjectType.PROGRAM:
            result = service.evaluate_program(
                profile=request.student,
                program_id=request.subject_id,
                rule_set_version=request.rule_set_version,
                evaluated_at=datetime.now(UTC),
            )
        else:
            result = service.evaluate_scholarship(
                profile=request.student, cycle_id=request.subject_id, evaluated_at=datetime.now(UTC)
            )
    except InvalidStudentReferenceError as exc:
        raise ApplicationError("INVALID_STUDENT_INPUT", str(exc), 422) from exc
    except RuleSetNotFoundError as exc:
        raise ApplicationError("NO_PUBLISHED_RULES", str(exc), 404) from exc
    return map_eligibility(result)
