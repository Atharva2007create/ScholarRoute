import { api } from "./client";
import type { CollegeRequest, RecommendationDetail, RecommendationPage, ScholarshipRequest } from "./types";

export const recommendColleges = (request: CollegeRequest) => api<RecommendationPage>("/api/v1/recommendations/colleges", { method: "POST", body: JSON.stringify(request) });
export const recommendScholarships = (request: ScholarshipRequest) => api<RecommendationPage>("/api/v1/recommendations/scholarships", { method: "POST", body: JSON.stringify(request) });
export const getRecommendation = (runId: string, position: number) => api<RecommendationDetail>(`/api/v1/recommendations/${runId}/${position}`);
