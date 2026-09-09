from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scholarroute.domain.eligibility.models import EligibilityStatus


class RankingDomain(StrEnum):
    COLLEGE = "COLLEGE"
    SCHOLARSHIP = "SCHOLARSHIP"


class RecommendationTier(StrEnum):
    SAFER = "SAFER"
    TARGET = "TARGET"
    REACH = "REACH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    STRONG_FIT = "STRONG_FIT"
    GOOD_FIT = "GOOD_FIT"
    POSSIBLE_FIT = "POSSIBLE_FIT"


class EvidenceConfidence(StrEnum):
    HIGH = "HIGH_CONFIDENCE"
    MEDIUM = "MEDIUM_CONFIDENCE"
    LOW = "LOW_CONFIDENCE"
    INSUFFICIENT = "INSUFFICIENT_DATA"


class RankingReason(StrEnum):
    EXACT_BRANCH_MATCH = "EXACT_BRANCH_MATCH"
    ALTERNATE_BRANCH = "ALTERNATE_BRANCH"
    STRONG_HISTORICAL_RANK_FIT = "STRONG_HISTORICAL_RANK_FIT"
    HISTORICALLY_COMPETITIVE = "HISTORICALLY_COMPETITIVE"
    HISTORICALLY_AMBITIOUS = "HISTORICALLY_AMBITIOUS"
    LIMITED_CUTOFF_HISTORY = "LIMITED_CUTOFF_HISTORY"
    WITHIN_BUDGET = "WITHIN_BUDGET"
    ABOVE_PREFERRED_BUDGET = "ABOVE_PREFERRED_BUDGET"
    FEE_DATA_MISSING = "FEE_DATA_MISSING"
    PREFERRED_STATE = "PREFERRED_STATE"
    PREFERRED_INSTITUTION_TYPE = "PREFERRED_INSTITUTION_TYPE"
    QUALITY_SIGNAL_AVAILABLE = "QUALITY_SIGNAL_AVAILABLE"
    HIGH_SCHOLARSHIP_BENEFIT = "HIGH_SCHOLARSHIP_BENEFIT"
    COURSE_RELEVANT = "COURSE_RELEVANT"
    INSTITUTION_COMPATIBLE = "INSTITUTION_COMPATIBLE"
    STATE_RELEVANT = "STATE_RELEVANT"
    APPLICATION_DEADLINE_SOON = "APPLICATION_DEADLINE_SOON"
    APPLICATION_UPCOMING = "APPLICATION_UPCOMING"
    BENEFIT_DATA_MISSING = "BENEFIT_DATA_MISSING"
    OPTIONAL_PREFERENCE_NOT_SET = "OPTIONAL_PREFERENCE_NOT_SET"


COLLEGE_COMPONENTS = frozenset(
    {"branch", "historical", "budget", "location", "institution", "quality"}
)
SCHOLARSHIP_COMPONENTS = frozenset({"benefit", "course", "institution", "state", "deadline"})


class RankingProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    version: str
    domain: RankingDomain
    weights: dict[str, Decimal]
    normalization_version: str = "linear-v1"
    tie_breaking_version: str = "stable-v1"

    @model_validator(mode="after")
    def validate_weights(self) -> RankingProfile:
        allowed = (
            COLLEGE_COMPONENTS if self.domain is RankingDomain.COLLEGE else SCHOLARSHIP_COMPONENTS
        )
        unknown = set(self.weights) - allowed
        if unknown:
            raise ValueError(f"unknown ranking components: {sorted(unknown)}")
        if not self.weights or any(weight < 0 for weight in self.weights.values()):
            raise ValueError("ranking weights must be present and non-negative")
        if sum(self.weights.values()) != Decimal("1"):
            raise ValueError("enabled ranking weights must sum exactly to 1")
        return self

    def snapshot_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class CollegePreferences(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    preferred_branch_codes: frozenset[str] = Field(default_factory=frozenset)
    alternate_branch_codes: frozenset[str] = Field(default_factory=frozenset)
    preferred_state_codes: frozenset[str] = Field(default_factory=frozenset)
    acceptable_state_codes: frozenset[str] = Field(default_factory=frozenset)
    preferred_institution_type_codes: frozenset[str] = Field(default_factory=frozenset)
    maximum_annual_budget: Decimal | None = Field(default=None, ge=0)


class ScholarshipPreferences(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    preferred_benefit_types: frozenset[str] = Field(default_factory=frozenset)
    preferred_state_codes: frozenset[str] = Field(default_factory=frozenset)
    target_program_id: UUID | None = None
    institution_type_code: str | None = None


@dataclass(frozen=True)
class RankingEvidence:
    source_document_version_id: UUID | None
    source_locator: str | None
    official_url: str | None
    academic_year: int | None = None


@dataclass(frozen=True)
class HistoricalCutoff:
    academic_year: int
    closing_rank: int
    round_sequence: int
    category_code: str
    quota_code: str
    gender_pool_code: str
    evidence: RankingEvidence


@dataclass(frozen=True)
class CollegeCandidate:
    program_id: UUID
    institution_id: UUID
    eligibility_evaluation_id: UUID
    eligibility_status: EligibilityStatus
    canonical_code: str
    branch_code: str | None
    state_code: str
    institution_type_code: str
    annual_fee: Decimal | None
    quality_signal: Decimal | None
    cutoffs: tuple[HistoricalCutoff, ...]
    official_links: tuple[str, ...]
    evidence: tuple[RankingEvidence, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScholarshipCandidate:
    scholarship_id: UUID
    eligibility_evaluation_id: UUID
    eligibility_status: EligibilityStatus
    canonical_code: str
    benefit_amount: Decimal | None
    benefit_type: str | None
    eligible_program_ids: frozenset[UUID]
    eligible_institution_types: frozenset[str]
    eligible_state_codes: frozenset[str]
    application_start_date: date | None
    deadline: date | None
    official_links: tuple[str, ...]
    evidence: tuple[RankingEvidence, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ComponentScore:
    name: str
    score: Decimal
    evidence_available: bool
    reasons: tuple[RankingReason, ...]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RankedResult:
    subject_id: UUID
    eligibility_evaluation_id: UUID
    rank_position: int
    overall_score: Decimal
    tier: RecommendationTier
    confidence: EvidenceConfidence
    components: tuple[ComponentScore, ...]
    reason_codes: tuple[RankingReason, ...]
    deterministic_summary: str
    official_links: tuple[str, ...]
    evidence: tuple[RankingEvidence, ...]
    ranking_profile_version: str


@dataclass(frozen=True)
class RankingOutcome:
    domain: RankingDomain
    profile_hash: str
    preference_hash: str
    evaluated_at: datetime
    ranked: tuple[RankedResult, ...]
    needs_information_ids: tuple[UUID, ...]
    excluded_ineligible_ids: tuple[UUID, ...]
    excluded_inactive_ids: tuple[UUID, ...] = ()


def preference_hash(preferences: BaseModel) -> str:
    payload = json.dumps(preferences.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
