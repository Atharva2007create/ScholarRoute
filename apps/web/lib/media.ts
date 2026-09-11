import type { Recommendation } from "./api/types";

export type ResultMedia = { url: string; kind: "campus" | "logo" } | null;

function safeMediaUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

export function selectResultMedia(item: Recommendation, scholarship: boolean): ResultMedia {
  if (!item.media_verified_at) return null;
  const campus = scholarship ? null : safeMediaUrl(item.campus_image_url);
  if (campus) return { url: campus, kind: "campus" };
  const logo = scholarship
    ? safeMediaUrl(item.scheme_logo_url ?? item.provider_logo_url)
    : safeMediaUrl(item.institution_logo_url);
  return logo ? { url: logo, kind: "logo" } : null;
}
