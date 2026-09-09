from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"


class RuleResultStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONFLICT = "CONFLICT"


class EligibilitySubjectType(StrEnum):
    PROGRAM = "PROGRAM"
    SCHOLARSHIP = "SCHOLARSHIP"


class RuleOperator(StrEnum):
    MINIMUM = "MINIMUM"
    MAXIMUM = "MAXIMUM"
    EQUALS = "EQUALS"
    ALLOWED_VALUES = "ALLOWED_VALUES"
    EXCLUDED_VALUES = "EXCLUDED_VALUES"
    REQUIRED_VALUES = "REQUIRED_VALUES"
    SUBJECT_MINIMUMS = "SUBJECT_MINIMUMS"
    BOOLEAN_EQUALS = "BOOLEAN_EQUALS"
    REQUIRED_CREDENTIAL = "REQUIRED_CREDENTIAL"
    ACHIEVEMENT_MINIMUM = "ACHIEVEMENT_MINIMUM"
    MINIMUM_AGE = "MINIMUM_AGE"
    MAXIMUM_AGE = "MAXIMUM_AGE"


class LogicalOperator(StrEnum):
    AND = "AND"
    OR = "OR"


class ReasonCode(StrEnum):
    PASS_MINIMUM_MARKS = "PASS_MINIMUM_MARKS"
    FAIL_MINIMUM_MARKS = "FAIL_MINIMUM_MARKS"
    MISSING_CLASS12_PERCENTAGE = "MISSING_CLASS12_PERCENTAGE"
    PASS_SUBJECT_MARKS = "PASS_SUBJECT_MARKS"
    FAIL_SUBJECT_MARKS = "FAIL_SUBJECT_MARKS"
    MISSING_SUBJECT_MARKS = "MISSING_SUBJECT_MARKS"
    PASS_REQUIRED_SUBJECTS = "PASS_REQUIRED_SUBJECTS"
    FAIL_REQUIRED_SUBJECTS = "FAIL_REQUIRED_SUBJECTS"
    MISSING_SUBJECTS = "MISSING_SUBJECTS"
    PASS_CATEGORY = "PASS_CATEGORY"
    FAIL_CATEGORY = "FAIL_CATEGORY"
    MISSING_CATEGORY = "MISSING_CATEGORY"
    PASS_DOMICILE = "PASS_DOMICILE"
    FAIL_DOMICILE = "FAIL_DOMICILE"
    MISSING_DOMICILE = "MISSING_DOMICILE"
    PASS_BOARD = "PASS_BOARD"
    FAIL_BOARD = "FAIL_BOARD"
    MISSING_BOARD = "MISSING_BOARD"
    PASS_QUALIFYING_EXAM = "PASS_QUALIFYING_EXAM"
    FAIL_QUALIFYING_EXAM = "FAIL_QUALIFYING_EXAM"
    MISSING_QUALIFYING_EXAM = "MISSING_QUALIFYING_EXAM"
    PASS_INCOME_LIMIT = "PASS_INCOME_LIMIT"
    FAIL_INCOME_LIMIT = "FAIL_INCOME_LIMIT"
    MISSING_FAMILY_INCOME = "MISSING_FAMILY_INCOME"
    PASS_GENDER = "PASS_GENDER"
    FAIL_GENDER = "FAIL_GENDER"
    MISSING_GENDER = "MISSING_GENDER"
    PASS_COURSE = "PASS_COURSE"
    FAIL_COURSE = "FAIL_COURSE"
    MISSING_COURSE = "MISSING_COURSE"
    PASS_INSTITUTION_TYPE = "PASS_INSTITUTION_TYPE"
    FAIL_INSTITUTION_TYPE = "FAIL_INSTITUTION_TYPE"
    MISSING_INSTITUTION_TYPE = "MISSING_INSTITUTION_TYPE"
    PASS_CREDENTIAL = "PASS_CREDENTIAL"
    FAIL_CREDENTIAL = "FAIL_CREDENTIAL"
    MISSING_CREDENTIAL = "MISSING_CREDENTIAL"
    PASS_ACHIEVEMENT = "PASS_ACHIEVEMENT"
    FAIL_ACHIEVEMENT = "FAIL_ACHIEVEMENT"
    MISSING_ACHIEVEMENT = "MISSING_ACHIEVEMENT"
    PASS_BOOLEAN_FLAG = "PASS_BOOLEAN_FLAG"
    FAIL_BOOLEAN_FLAG = "FAIL_BOOLEAN_FLAG"
    MISSING_BOOLEAN_FLAG = "MISSING_BOOLEAN_FLAG"
    PASS_SCORE = "PASS_SCORE"
    FAIL_SCORE = "FAIL_SCORE"
    MISSING_SCORE = "MISSING_SCORE"
    PASS_RANK = "PASS_RANK"
    FAIL_RANK = "FAIL_RANK"
    MISSING_RANK = "MISSING_RANK"
    PASS_AGE = "PASS_AGE"
    FAIL_AGE = "FAIL_AGE"
    MISSING_DATE_OF_BIRTH = "MISSING_DATE_OF_BIRTH"
    RULE_GROUP_PASSED = "RULE_GROUP_PASSED"
    RULE_GROUP_FAILED = "RULE_GROUP_FAILED"
    RULE_GROUP_MISSING = "RULE_GROUP_MISSING"
    RULE_CONFLICT = "RULE_CONFLICT"
    RULE_NOT_APPLICABLE = "RULE_NOT_APPLICABLE"


class StudentEligibilityInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str | None = None
    snapshot_version: str = "1"
    evaluation_year: int = Field(ge=2000, le=2100)
    evaluation_date: date | None = None
    exam_code: str | None = None
    exam_rank: int | None = Field(default=None, gt=0)
    exam_score: Decimal | None = Field(default=None, ge=0)
    exam_percentile: Decimal | None = Field(default=None, ge=0, le=100)
    category_code: str | None = None
    sub_category_code: str | None = None
    quota_code: str | None = None
    gender_code: str | None = None
    gender_pool_code: str | None = None
    state_code: str | None = None
    domicile_state_code: str | None = None
    board_code: str | None = None
    class12_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    subject_marks: dict[str, Decimal] | None = None
    subjects_studied: frozenset[str] | None = None
    family_income: Decimal | None = Field(default=None, ge=0)
    target_course_code: str | None = None
    target_program_id: UUID | None = None
    institution_type_code: str | None = None
    achievements: dict[str, Decimal] | None = None
    credentials: frozenset[str] | None = None
    is_pwd: bool | None = None
    is_ews: bool | None = None
    nationality_code: str | None = None
    date_of_birth: date | None = None

    @field_validator(
        "exam_code",
        "category_code",
        "sub_category_code",
        "quota_code",
        "gender_code",
        "gender_pool_code",
        "state_code",
        "domicile_state_code",
        "board_code",
        "target_course_code",
        "institution_type_code",
        "nationality_code",
        mode="before",
    )
    @classmethod
    def normalize_code(cls, value: object) -> object:
        if value is None:
            return None
        normalized = str(value).strip().upper().replace("-", "_").replace(" ", "_")
        if not normalized or not normalized.replace("_", "").isalnum():
            raise ValueError("controlled-vocabulary codes must be alphanumeric with underscores")
        return normalized

    @field_validator("subject_marks", "achievements", mode="before")
    @classmethod
    def normalize_mapping_keys(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        return {str(key).strip().upper().replace("-", "_"): item for key, item in value.items()}

    @field_validator("subjects_studied", "credentials", mode="before")
    @classmethod
    def normalize_set_values(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, (set, frozenset, list, tuple)):
            raise ValueError("value must be a collection of controlled-vocabulary codes")
        return {str(item).strip().upper().replace("-", "_") for item in value}

    @model_validator(mode="after")
    def validate_subject_marks(self) -> Self:
        if self.subject_marks is not None:
            invalid = [name for name, mark in self.subject_marks.items() if not 0 <= mark <= 100]
            if invalid:
                raise ValueError(f"subject marks must be between 0 and 100: {invalid}")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=False)

    def content_hash(self) -> str:
        payload = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class RuleEvidence:
    source_document_version_id: UUID | None
    source_authority: str | None
    source_document: str | None
    source_locator: str | None
    official_url: str | None
    applicable_year: int
    rule_version: str
    verified_at: datetime | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class RuleScope:
    evaluation_year: int
    subject_type: EligibilitySubjectType
    subject_id: UUID | None = None
    exam_code: str | None = None
    authority_code: str | None = None
    institution_id: UUID | None = None
    program_id: UUID | None = None
    scholarship_id: UUID | None = None
    category_code: str | None = None
    quota_code: str | None = None
    domicile_state_code: str | None = None

    @property
    def specificity(self) -> int:
        weights = (
            (self.subject_id, 1),
            (self.exam_code, 2),
            (self.authority_code, 2),
            (self.institution_id, 4),
            (self.program_id, 8),
            (self.scholarship_id, 8),
            (self.category_code, 2),
            (self.quota_code, 2),
            (self.domicile_state_code, 2),
        )
        return sum(weight for value, weight in weights if value is not None)


@dataclass(frozen=True)
class CandidateContext:
    subject_type: EligibilitySubjectType
    subject_id: UUID
    evaluation_year: int
    exam_code: str | None = None
    authority_code: str | None = None
    institution_id: UUID | None = None
    program_id: UUID | None = None
    scholarship_id: UUID | None = None
    quota_code: str | None = None


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    version: str
    key: str
    operator: RuleOperator
    field_name: str
    expected: Any
    description: str
    pass_reason: ReasonCode
    fail_reason: ReasonCode
    missing_reason: ReasonCode
    scope: RuleScope
    evidence: RuleEvidence


@dataclass(frozen=True)
class RuleGroup:
    rule_id: str
    version: str
    key: str
    operator: LogicalOperator
    children: tuple[RuleDefinition | RuleGroup, ...]
    description: str
    scope: RuleScope
    evidence: RuleEvidence


RuleNode = RuleDefinition | RuleGroup


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    rule_version: str
    status: RuleResultStatus
    reason_code: ReasonCode
    message: str
    observed_value: Any = None
    expected_value: Any = None
    evidence: RuleEvidence | None = None
    children: tuple[RuleEvaluation, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuleSet:
    version: str
    rules: tuple[RuleNode, ...]
    catalog_release_id: UUID | None = None


@dataclass(frozen=True)
class EligibilityDecision:
    status: EligibilityStatus
    subject_type: EligibilitySubjectType
    subject_id: UUID
    evaluation_year: int
    student_snapshot_hash: str
    rule_set_version: str
    evaluated_at: datetime
    evaluations: tuple[RuleEvaluation, ...]
    reason_codes: tuple[ReasonCode, ...]
    missing_information: tuple[str, ...]
    human_summary: str
    catalog_release_id: UUID | None = None
