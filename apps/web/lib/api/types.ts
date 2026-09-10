export type ReferenceItem = { id: string; code: string; name: string };
export type PageMeta = { total: number; limit: number; offset: number };
export type ReferencePage = { results: ReferenceItem[]; meta: PageMeta };

export type StudentInput = {
  evaluation_year: number;
  evaluation_date?: string;
  exam_code?: string;
  exam_rank?: number;
  exam_score?: number;
  exam_percentile?: number;
  category_code?: string;
  quota_code?: string;
  gender_code?: string;
  gender_pool_code?: string;
  state_code?: string;
  domicile_state_code?: string;
  board_code?: string;
  class12_percentage?: number;
  family_income?: number;
  target_course_code?: string;
  institution_type_code?: string;
  is_pwd?: boolean;
  is_ews?: boolean;
};

export type CollegeRequest = {
  student: StudentInput;
  preferences: {
    preferred_branch_codes: string[];
    alternate_branch_codes: string[];
    preferred_state_codes: string[];
    preferred_institution_type_codes: string[];
    maximum_annual_budget?: number;
  };
  preset: "BALANCED" | "BRANCH_FIRST" | "BUDGET_FIRST" | "LOCATION_FIRST";
  state_code?: string;
  branch_code?: string;
  institution_type_code?: string;
  limit: number;
  offset: number;
};

export type ScholarshipRequest = {
  student: StudentInput;
  preferences: {
    preferred_benefit_types: string[];
    preferred_state_codes: string[];
    institution_type_code?: string;
  };
  preset: "BALANCED";
  benefit_type?: string;
  provider_code?: string;
  limit: number;
  offset: number;
};

export type Evidence = {
  source_document_version_id: string | null;
  source_locator: string | null;
  official_url: string | null;
  applicable_year: number | null;
  rule_version: string | null;
};

export type ScoreComponent = {
  name: string;
  score: string;
  evidence_available: boolean;
  reason_codes: string[];
  details: Record<string, unknown>;
};

export type Recommendation = {
  subject_id: string;
  eligibility_evaluation_id: string;
  rank_position: number;
  fit_score: string;
  tier: string;
  confidence: string;
  components: ScoreComponent[];
  reason_codes: string[];
  summary: string;
  official_links: string[];
  evidence: Evidence[];
  ranking_profile_version: string;
  title: string | null;
  organization: string | null;
  state_code: string | null;
  annual_fee: string | null;
  benefit_amount: string | null;
  deadline: string | null;
  institution_logo_url?: string | null;
  campus_image_url?: string | null;
  provider_logo_url?: string | null;
  scheme_logo_url?: string | null;
  media_source_url?: string | null;
  media_verified_at?: string | null;
};

export type RecommendationPage = {
  results: Recommendation[];
  meta: PageMeta & {
    ranking_run_id: string;
    ranking_profile: string;
    needs_information: string[];
    excluded_ineligible: number;
    excluded_inactive: number;
  };
};

export type RecommendationDetail = { ranking_run_id: string; result: Recommendation };
export type ApiErrorBody = { error: { code: string; message: string; request_id: string; fields: { path: string; code: string }[] } };
