from __future__ import annotations

import logging
import re
from time import perf_counter
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from scholarroute.application.ai.models import (
    AuthoritativeFacts,
    ExplanationContent,
    ExplanationResponse,
)
from scholarroute.application.ai.prompts import SYSTEM_INSTRUCTION, ExplanationKind, build_prompt
from scholarroute.application.ai.provider import AIProvider, AIProviderError, GeminiProvider
from scholarroute.config import Settings
from scholarroute.errors import ApplicationError
from scholarroute.infrastructure.db.models import (
    EligibilityEvaluation,
    EligibilityEvaluationResourceLink,
    EligibilityRuleResult,
    Institution,
    Program,
    RankedRecommendation,
    RankingRun,
    ResourceLink,
    ScholarshipCycle,
    ScholarshipProvider,
    ScholarshipScheme,
)
from scholarroute.infrastructure.db.models.enums import RankingDomain

logger = logging.getLogger(__name__)
_UNSAFE_GENERATED_TEXT = re.compile(
    r"(?:https?://|www\.|\b\d+(?:\.\d+)?\s*%\s+(?:chance|probability)|guaranteed admission)",
    re.IGNORECASE,
)


class AIExplanationService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        provider: AIProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider

    def explain_recommendation(
        self, kind: ExplanationKind, run_id: UUID, position: int
    ) -> ExplanationResponse:
        if kind not in {"college", "scholarship"}:
            raise ValueError("Recommendation explanations must be college or scholarship")
        row = self.session.execute(
            select(RankedRecommendation, RankingRun, EligibilityEvaluation)
            .join(RankingRun, RankingRun.id == RankedRecommendation.ranking_run_id)
            .join(
                EligibilityEvaluation,
                EligibilityEvaluation.id == RankedRecommendation.eligibility_evaluation_id,
            )
            .where(
                RankedRecommendation.ranking_run_id == run_id,
                RankedRecommendation.rank_position == position,
            )
        ).one_or_none()
        expected_domain = RankingDomain.COLLEGE if kind == "college" else RankingDomain.SCHOLARSHIP
        if row is None or row.RankingRun.domain is not expected_domain:
            raise ApplicationError("RESOURCE_NOT_FOUND", "Recommendation result not found", 404)
        record, run, evaluation = row
        identity = self._subject_identity(kind, record.subject_id)
        context = {
            "identity": identity,
            "deterministic_result": {
                "eligibility_status": evaluation.status.value,
                "fit_score": str(record.overall_score),
                "tier": record.tier,
                "confidence": record.confidence,
                "summary": record.deterministic_summary,
                "reason_codes": record.reason_codes,
                "components": record.component_scores,
                "ranking_profile_version": str(run.ranking_profile_snapshot.get("version", "")),
            },
            "evidence": [
                {
                    "source_document_version_id": item.get("source_document_version_id"),
                    "source_locator": item.get("source_locator"),
                    "applicable_year": item.get("applicable_year"),
                    "rule_version": item.get("rule_version"),
                }
                for item in record.evidence
            ],
        }
        content, version = self._generate(kind, context)
        return ExplanationResponse(
            explanation_type=kind,
            model=self.settings.gemini_model,
            prompt_version=version,
            explanation=content,
            authoritative=AuthoritativeFacts(
                recommendation_id=record.id,
                eligibility_evaluation_id=evaluation.id,
                subject_id=record.subject_id,
                fit_score=record.overall_score,
                tier=record.tier,
                confidence=record.confidence,
                eligibility_status=evaluation.status.value,
                ranking_profile_version=str(run.ranking_profile_snapshot.get("version", "")),
            ),
            official_links=list(record.official_links),
        )

    def explain_eligibility(self, evaluation_id: UUID) -> ExplanationResponse:
        evaluation = self.session.get(EligibilityEvaluation, evaluation_id)
        if evaluation is None:
            raise ApplicationError("RESOURCE_NOT_FOUND", "Eligibility evaluation not found", 404)
        rules = list(
            self.session.scalars(
                select(EligibilityRuleResult)
                .where(EligibilityRuleResult.evaluation_id == evaluation_id)
                .order_by(EligibilityRuleResult.sequence)
            )
        )
        official_links = list(
            self.session.scalars(
                select(ResourceLink.url)
                .join(
                    EligibilityEvaluationResourceLink,
                    EligibilityEvaluationResourceLink.resource_link_id == ResourceLink.id,
                )
                .where(EligibilityEvaluationResourceLink.evaluation_id == evaluation_id)
            )
        )
        official_links.extend(item.official_url for item in rules if item.official_url)
        context = {
            "subject_type": evaluation.subject_type.value,
            "subject_id": str(evaluation.subject_id),
            "status": evaluation.status.value,
            "summary": evaluation.human_summary,
            "reason_codes": evaluation.reason_codes,
            "missing_information": evaluation.missing_information,
            "rule_set_version": evaluation.rule_set_version,
            "rules": [
                {
                    "rule_id": item.rule_id,
                    "status": item.status.value,
                    "reason_code": item.reason_code,
                    "message": item.message,
                    "source_locator": item.source_locator,
                    "rule_version": item.rule_version,
                }
                for item in rules
            ],
        }
        content, version = self._generate("eligibility", context)
        return ExplanationResponse(
            explanation_type="eligibility",
            model=self.settings.gemini_model,
            prompt_version=version,
            explanation=content,
            authoritative=AuthoritativeFacts(
                eligibility_evaluation_id=evaluation.id,
                subject_id=evaluation.subject_id,
                eligibility_status=evaluation.status.value,
            ),
            official_links=list(dict.fromkeys(official_links)),
        )

    def _subject_identity(self, kind: ExplanationKind, subject_id: UUID) -> dict[str, Any]:
        if kind == "college":
            college_row = self.session.execute(
                select(Program.name, Program.code, Institution.official_name)
                .join(Institution, Institution.id == Program.institution_id)
                .where(Program.id == subject_id)
            ).one_or_none()
            if college_row is None:
                return {"subject_id": str(subject_id)}
            return {
                "program": college_row.name,
                "program_code": college_row.code,
                "institution": college_row.official_name,
            }
        scholarship_row = self.session.execute(
            select(
                ScholarshipScheme.name,
                ScholarshipScheme.official_code,
                ScholarshipProvider.name.label("provider"),
                ScholarshipCycle.academic_year,
                ScholarshipCycle.deadline,
            )
            .join(ScholarshipScheme, ScholarshipScheme.id == ScholarshipCycle.scheme_id)
            .join(ScholarshipProvider, ScholarshipProvider.id == ScholarshipScheme.provider_id)
            .where(ScholarshipCycle.id == subject_id)
        ).one_or_none()
        if scholarship_row is None:
            return {"subject_id": str(subject_id)}
        return {
            "scholarship": scholarship_row.name,
            "official_code": scholarship_row.official_code,
            "provider": scholarship_row.provider,
            "academic_year": scholarship_row.academic_year,
            "deadline": scholarship_row.deadline,
        }

    def _generate(
        self, kind: ExplanationKind, context: dict[str, Any]
    ) -> tuple[ExplanationContent, str]:
        self._check_available()
        version, prompt = build_prompt(kind, context)
        provider = self.provider
        if provider is None:
            configured_key = self.settings.gemini_api_key
            assert configured_key is not None
            key = configured_key.get_secret_value()
            provider = GeminiProvider(key)
        started = perf_counter()
        last_error: AIProviderError | None = None
        attempts = self.settings.ai_max_retries + 1
        for attempt in range(attempts):
            try:
                raw = provider.generate(
                    model=self.settings.gemini_model,
                    system_instruction=SYSTEM_INSTRUCTION,
                    prompt=prompt,
                    response_schema=ExplanationContent,
                    timeout_seconds=self.settings.ai_timeout_seconds,
                    max_output_tokens=self.settings.ai_max_output_tokens,
                )
                content = self._parse_and_validate(raw)
                logger.info(
                    "ai_explanation_completed",
                    extra={
                        "explanation_type": kind,
                        "model": self.settings.gemini_model,
                        "prompt_version": version,
                        "latency_ms": round((perf_counter() - started) * 1000, 2),
                        "retry_count": attempt,
                    },
                )
                return content, version
            except AIProviderError as exc:
                last_error = exc
                if not exc.transient or attempt == attempts - 1:
                    break
            except (ValidationError, ValueError, TypeError) as exc:
                raise ApplicationError(
                    "AI_INVALID_RESPONSE",
                    "AI explanation is temporarily unavailable. "
                    "Your ScholarRoute result is still valid.",
                    502,
                ) from exc
        assert last_error is not None
        logger.warning(
            "ai_explanation_failed",
            extra={
                "explanation_type": kind,
                "model": self.settings.gemini_model,
                "prompt_version": version,
                "failure_category": last_error.category,
                "retry_count": attempts - 1,
            },
        )
        if last_error.category == "rate_limited":
            status_code = 429
        elif last_error.category == "timeout":
            status_code = 504
        elif last_error.category == "empty_response":
            status_code = 502
        else:
            status_code = 503
        code = {
            "rate_limited": "AI_RATE_LIMITED",
            "timeout": "AI_TIMEOUT",
            "invalid_credentials": "AI_NOT_CONFIGURED",
            "empty_response": "AI_INVALID_RESPONSE",
        }.get(last_error.category, "AI_UNAVAILABLE")
        raise ApplicationError(
            code,
            "AI explanation is temporarily unavailable. Your ScholarRoute result is still valid.",
            status_code,
        )

    def _check_available(self) -> None:
        if not self.settings.ai_enabled:
            raise ApplicationError(
                "AI_DISABLED",
                "AI explanation is disabled. Your ScholarRoute result is still valid.",
                503,
            )
        if (
            self.settings.gemini_api_key is None
            or not self.settings.gemini_api_key.get_secret_value()
        ):
            raise ApplicationError(
                "AI_NOT_CONFIGURED",
                "AI explanation is not configured. Your ScholarRoute result is still valid.",
                503,
            )

    @staticmethod
    def _parse_and_validate(raw: Any) -> ExplanationContent:
        if isinstance(raw, ExplanationContent):
            content = raw
        elif isinstance(raw, str):
            if not raw.strip():
                raise ValueError("Empty response")
            content = ExplanationContent.model_validate_json(raw)
        elif isinstance(raw, dict):
            content = ExplanationContent.model_validate(raw)
        elif isinstance(raw, BaseException):
            raise TypeError("Invalid provider response")
        else:
            content = ExplanationContent.model_validate(raw)
        generated = " ".join(
            [content.summary, *content.reasons, *content.caveats, *content.next_steps]
        )
        if _UNSAFE_GENERATED_TEXT.search(generated):
            raise ValueError("Generated output attempted to introduce unsafe claims or URLs")
        return content
