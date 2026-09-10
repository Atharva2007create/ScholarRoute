import type { CollegeRequest, RecommendationPage, ScholarshipRequest } from "./api/types";

export type SearchKind = "colleges" | "scholarships";
export type StoredSearch<T> = { request: T; response: RecommendationPage; labels: Record<string, string> };
const key = (kind: SearchKind) => `scholarroute:${kind}:search`;
export function saveSearch<T extends CollegeRequest | ScholarshipRequest>(kind: SearchKind, value: StoredSearch<T>) { sessionStorage.setItem(key(kind), JSON.stringify(value)); }
export function loadSearch<T extends CollegeRequest | ScholarshipRequest>(kind: SearchKind): StoredSearch<T> | null {
  const value = sessionStorage.getItem(key(kind));
  if (!value) return null;
  try { return JSON.parse(value) as StoredSearch<T>; } catch { return null; }
}
