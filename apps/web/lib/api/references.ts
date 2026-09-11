import { api } from "./client";
import type { ReferencePage } from "./types";

export const referenceResources = ["exams", "states", "categories", "quotas", "institution-types", "courses", "admission-years"] as const;
export type ReferenceResource = (typeof referenceResources)[number];
export const getReference = (resource: ReferenceResource) => api<ReferencePage>(`/api/v1/reference/${resource}?limit=100`);
export const getBranches = (courseId: string) => api<ReferencePage>(`/api/v1/reference/branches/by-course/${courseId}?limit=100`);
