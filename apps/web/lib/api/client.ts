import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  public readonly code: string;
  public readonly requestId?: string;
  constructor(message: string, code: string, requestId?: string) {
    super(message);
    this.code = code;
    this.requestId = requestId;
  }
}

const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let body: ApiErrorBody | undefined;
    try { body = (await response.json()) as ApiErrorBody; } catch { /* non-JSON gateway failure */ }
    throw new ApiError(body?.error.message ?? "The ScholarRoute service is unavailable.", body?.error.code ?? "REQUEST_FAILED", body?.error.request_id);
  }
  return response.json() as Promise<T>;
}

export function safeOfficialUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch { return null; }
}
