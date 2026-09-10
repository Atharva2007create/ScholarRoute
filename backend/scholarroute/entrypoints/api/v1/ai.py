from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from scholarroute.application.ai.models import ExplanationResponse
from scholarroute.application.ai.service import AIExplanationService
from scholarroute.config import Settings, get_settings
from scholarroute.entrypoints.api.dependencies import SessionDependency

router = APIRouter(prefix="/api/v1/ai/explain", tags=["AI Explanations"])


class RecommendationExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ranking_run_id: UUID
    rank_position: int = Field(ge=1)


class EligibilityExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_id: UUID


def get_ai_explanation_service(
    session: SessionDependency, settings: Annotated[Settings, Depends(get_settings)]
) -> AIExplanationService:
    return AIExplanationService(session, settings)


AIServiceDependency = Annotated[AIExplanationService, Depends(get_ai_explanation_service)]


def _recommendation(
    kind: Literal["college", "scholarship"],
    request: RecommendationExplanationRequest,
    service: AIServiceDependency,
) -> ExplanationResponse:
    return service.explain_recommendation(kind, request.ranking_run_id, request.rank_position)


@router.post("/college", response_model=ExplanationResponse, summary="Explain a college result")
def explain_college(
    request: RecommendationExplanationRequest, service: AIServiceDependency
) -> ExplanationResponse:
    return _recommendation("college", request, service)


@router.post(
    "/scholarship", response_model=ExplanationResponse, summary="Explain a scholarship result"
)
def explain_scholarship(
    request: RecommendationExplanationRequest, service: AIServiceDependency
) -> ExplanationResponse:
    return _recommendation("scholarship", request, service)


@router.post(
    "/eligibility", response_model=ExplanationResponse, summary="Explain an eligibility result"
)
def explain_eligibility(
    request: EligibilityExplanationRequest, service: AIServiceDependency
) -> ExplanationResponse:
    return service.explain_eligibility(request.evaluation_id)
