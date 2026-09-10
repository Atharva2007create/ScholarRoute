from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from scholarroute.domain.eligibility.models import EligibilitySubjectType, StudentEligibilityInput
from scholarroute.domain.ranking.models import CollegePreferences, ScholarshipPreferences


class PageParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ReferenceItem(BaseModel):
    id: UUID
    code: str
    name: str


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int


class ReferencePage(BaseModel):
    results: list[ReferenceItem]
    meta: PageMeta


class EligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_type: EligibilitySubjectType
    subject_id: UUID
    student: StudentEligibilityInput
    rule_set_version: str | None = None


class EvidenceResponse(BaseModel):
    source_document_version_id: UUID | None = None
    source_locator: str | None = None
    official_url: str | None = None
    applicable_year: int | None = None
    rule_version: str | None = None


class RuleResponse(BaseModel):
    rule_id: str
    status: str
    reason_code: str
    message: str
    evidence: EvidenceResponse | None = None


class EligibilityResponse(BaseModel):
    evaluation_id: UUID
    subject_type: str
    subject_id: UUID
    status: str
    reason_codes: list[str]
    missing_information: list[str]
    summary: str
    rule_set_version: str
    evaluated_at: datetime
    rules: list[RuleResponse]
    official_links: list[str]


class CollegeRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student: StudentEligibilityInput
    preferences: CollegePreferences = Field(default_factory=CollegePreferences)
    preset: Literal["BALANCED", "BRANCH_FIRST", "BUDGET_FIRST", "LOCATION_FIRST"] = "BALANCED"
    state_code: str | None = None
    branch_code: str | None = None
    institution_type_code: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ScholarshipRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student: StudentEligibilityInput
    preferences: ScholarshipPreferences = Field(default_factory=ScholarshipPreferences)
    preset: Literal["BALANCED"] = "BALANCED"
    benefit_type: str | None = None
    provider_code: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ComponentResponse(BaseModel):
    name: str
    score: Decimal
    evidence_available: bool
    reason_codes: list[str]
    details: dict[str, Any]


class RecommendationResponse(BaseModel):
    subject_id: UUID
    eligibility_evaluation_id: UUID
    rank_position: int
    fit_score: Decimal
    tier: str
    confidence: str
    components: list[ComponentResponse]
    reason_codes: list[str]
    summary: str
    official_links: list[str]
    evidence: list[EvidenceResponse]
    ranking_profile_version: str
    title: str | None = None
    organization: str | None = None
    state_code: str | None = None
    annual_fee: Decimal | None = None
    benefit_amount: Decimal | None = None
    deadline: date | None = None


class RecommendationMeta(PageMeta):
    ranking_run_id: UUID
    ranking_profile: str
    needs_information: list[UUID]
    excluded_ineligible: int
    excluded_inactive: int


class RecommendationPage(BaseModel):
    results: list[RecommendationResponse]
    meta: RecommendationMeta


class RecommendationDetail(BaseModel):
    ranking_run_id: UUID
    result: RecommendationResponse
