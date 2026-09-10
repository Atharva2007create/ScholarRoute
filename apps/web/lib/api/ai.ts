import { api } from "./client";
import type { AIExplanation } from "./types";

export function explainRecommendation(
  kind: "college" | "scholarship",
  rankingRunId: string,
  rankPosition: number,
) {
  return api<AIExplanation>(`/api/v1/ai/explain/${kind}`, {
    method: "POST",
    body: JSON.stringify({ ranking_run_id: rankingRunId, rank_position: rankPosition }),
  });
}

export function explainEligibility(evaluationId: string) {
  return api<AIExplanation>("/api/v1/ai/explain/eligibility", {
    method: "POST",
    body: JSON.stringify({ evaluation_id: evaluationId }),
  });
}
