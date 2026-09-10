from typing import Any
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from scholarroute.application.discovery.service import DiscoveryResult, DiscoveryService
from scholarroute.entrypoints.api.dependencies import SessionDependency
from scholarroute.entrypoints.api.v1.schemas import (
    CollegeRecommendationRequest,
    ComponentResponse,
    EvidenceResponse,
    RecommendationDetail,
    RecommendationMeta,
    RecommendationPage,
    RecommendationResponse,
    ScholarshipRecommendationRequest,
)
from scholarroute.errors import ApplicationError
from scholarroute.infrastructure.db.models import RankedRecommendation, RankingRun

router = APIRouter(prefix="/api/v1/recommendations")


def _map_result(item: Any, detail: dict[str, Any] | None = None) -> RecommendationResponse:
    detail = detail or {}
    return RecommendationResponse(
        subject_id=item.subject_id,
        eligibility_evaluation_id=item.eligibility_evaluation_id,
        rank_position=item.rank_position,
        fit_score=item.overall_score,
        tier=item.tier.value,
        confidence=item.confidence.value,
        components=[
            ComponentResponse(
                name=part.name,
                score=part.score,
                evidence_available=part.evidence_available,
                reason_codes=[reason.value for reason in part.reasons],
                details=part.details,
            )
            for part in item.components
        ],
        reason_codes=[reason.value for reason in item.reason_codes],
        summary=item.deterministic_summary,
        official_links=list(item.official_links),
        evidence=[
            EvidenceResponse(
                source_document_version_id=evidence.source_document_version_id,
                source_locator=evidence.source_locator,
                official_url=evidence.official_url,
                applicable_year=evidence.academic_year,
            )
            for evidence in item.evidence
        ],
        ranking_profile_version=item.ranking_profile_version,
        **detail,
    )


def _page(discovery: DiscoveryResult, limit: int, offset: int) -> RecommendationPage:
    outcome = discovery.ranking.outcome
    selected = outcome.ranked[offset : offset + limit]
    return RecommendationPage(
        results=[_map_result(item, discovery.details.get(item.subject_id)) for item in selected],
        meta=RecommendationMeta(
            total=len(outcome.ranked),
            limit=limit,
            offset=offset,
            ranking_run_id=discovery.ranking.run_id,
            ranking_profile=outcome.ranked[0].ranking_profile_version
            if outcome.ranked
            else "2026.1",
            needs_information=list(outcome.needs_information_ids),
            excluded_ineligible=len(outcome.excluded_ineligible_ids),
            excluded_inactive=len(outcome.excluded_inactive_ids),
        ),
    )


@router.post(
    "/colleges",
    response_model=RecommendationPage,
    tags=["College Recommendations"],
    summary="Rank eligible college programs",
)
def colleges(
    request: CollegeRecommendationRequest, session: SessionDependency
) -> RecommendationPage:
    try:
        result = DiscoveryService(session).colleges(
            student=request.student,
            preferences=request.preferences,
            preset=request.preset,
            state_code=request.state_code,
            branch_code=request.branch_code,
            institution_type_code=request.institution_type_code,
        )
    except ValueError as exc:
        raise ApplicationError("INVALID_STUDENT_INPUT", str(exc), 422) from exc
    return _page(result, request.limit, request.offset)


@router.post(
    "/scholarships",
    response_model=RecommendationPage,
    tags=["Scholarship Recommendations"],
    summary="Rank eligible scholarships",
)
def scholarships(
    request: ScholarshipRecommendationRequest, session: SessionDependency
) -> RecommendationPage:
    try:
        result = DiscoveryService(session).scholarships(
            student=request.student,
            preferences=request.preferences,
            benefit_type=request.benefit_type,
            provider_code=request.provider_code,
        )
    except ValueError as exc:
        raise ApplicationError("INVALID_STUDENT_INPUT", str(exc), 422) from exc
    return _page(result, request.limit, request.offset)


@router.get(
    "/{run_id}/{position}",
    response_model=RecommendationDetail,
    tags=["Recommendation Evidence"],
    summary="Get a persisted recommendation result",
)
def detail(run_id: UUID, position: int, session: SessionDependency) -> RecommendationDetail:
    row = session.execute(
        select(RankedRecommendation, RankingRun)
        .join(RankingRun, RankingRun.id == RankedRecommendation.ranking_run_id)
        .where(
            RankedRecommendation.ranking_run_id == run_id,
            RankedRecommendation.rank_position == position,
        )
    ).one_or_none()
    if row is None:
        raise ApplicationError("RESOURCE_NOT_FOUND", "Recommendation result not found", 404)
    record, run = row
    result = RecommendationResponse(
        subject_id=record.subject_id,
        eligibility_evaluation_id=record.eligibility_evaluation_id,
        rank_position=record.rank_position,
        fit_score=record.overall_score,
        tier=record.tier,
        confidence=record.confidence,
        components=[
            ComponentResponse(
                name=item["name"],
                score=item["score"],
                evidence_available=item["evidence_available"],
                reason_codes=item["reasons"],
                details=item["details"],
            )
            for item in record.component_scores
        ],
        reason_codes=record.reason_codes,
        summary=record.deterministic_summary,
        official_links=record.official_links,
        evidence=[EvidenceResponse(**item) for item in record.evidence],
        ranking_profile_version=str(run.ranking_profile_snapshot["version"]),
    )
    return RecommendationDetail(ranking_run_id=run_id, result=result)
