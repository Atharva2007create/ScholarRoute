# ScholarRoute API design

## Boundary

Expose a versioned REST/JSON API under `/v1`. Publish OpenAPI from FastAPI and generate the TypeScript client/types consumed by Next.js. Frontend types must not be handwritten copies of backend schemas.

Routes call application services; they cannot query ORM models directly or contain eligibility/ranking logic. Public identifiers use opaque UUIDs. All timestamps are ISO 8601 with offsets and all money includes currency and period.

## Initial resources

| Method and route | Purpose | Auth |
|---|---|---|
| `GET /v1/catalog/exams` | Supported exam/year choices | Public, rate-limited |
| `GET /v1/catalog/boards` | Supported boards and required subject fields | Public, rate-limited |
| `GET /v1/catalog/states` | Canonical domicile/location choices | Public, rate-limited |
| `GET /v1/catalog/courses` | Course and branch choices for a cycle | Public, rate-limited |
| `POST /v1/profiles` | Create a saved profile | User |
| `GET /v1/profiles/{id}` | Read an owned profile | Owner |
| `PATCH /v1/profiles/{id}` | Update fields using optimistic concurrency | Owner |
| `DELETE /v1/profiles/{id}` | Delete/anonymize according to retention policy | Owner |
| `POST /v1/recommendations/colleges` | Run college eligibility/matching/ranking | User; preview policy TBD |
| `POST /v1/recommendations/scholarships` | Run scholarship eligibility/matching/ranking | User; preview policy TBD |
| `GET /v1/recommendation-runs/{id}` | Retrieve an owned reproducible run | Owner |
| `POST /v1/recommendation-runs/{id}/explanations` | Optional generated wording for existing facts | Owner |
| `GET /v1/sources/{document_version_id}` | Safe provenance metadata and official link | Public, rate-limited |
| `POST /v1/admin/ingestion-runs` | Trigger a registered ingestion job | Admin |
| `GET /v1/admin/review-items` | Review staged changes/findings | Reviewer |
| `POST /v1/admin/releases/{id}/approve` | Record approval | Reviewer |
| `POST /v1/admin/releases/{id}/publish` | Atomically activate an approved release | Publisher |

The admin endpoints can start as API-only operations behind strict roles. A review UI follows after ingestion correctness is established.

## Recommendation request

Accept either `profile_id` with expected revision or an inline `profile` snapshot, plus explicit scope and preferences. Do not mix an old saved profile with silent current values.

```json
{
  "profile_id": "uuid",
  "profile_revision": 4,
  "scope": {
    "exam_code": "JEE_MAIN",
    "admission_year": 2027,
    "course_code": "BTECH"
  },
  "preferences": {
    "ranking_policy": "BALANCED_V1",
    "branch_ids": ["uuid"],
    "preferred_state_ids": ["uuid"],
    "annual_budget": {"amount": "250000.00", "currency": "INR"}
  },
  "page": {"limit": 25, "cursor": null}
}
```

The server selects the active compatible catalog/rule versions and returns them. An admin/debug-only interface may pin older versions; ordinary clients cannot select arbitrary draft releases.

## Recommendation response

```json
{
  "run_id": "uuid",
  "generated_at": "2026-09-09T12:00:00Z",
  "versions": {
    "catalog_release": "JOSAA-2027.3",
    "rule_sets": ["JOSAA-2027.2"],
    "ranking_policy": "BALANCED_V1"
  },
  "results": [
    {
      "target": {"type": "PROGRAM_OFFERING", "id": "uuid"},
      "eligibility": "ELIGIBLE",
      "rank_position": 1,
      "score": "0.8421",
      "reasons": [{"code": "BRANCH_PREFERENCE_MATCH", "text": "Matches your selected branch"}],
      "score_components": [],
      "caveats": [],
      "sources": [{"document_version_id": "uuid", "locator": "table 3, row 18"}]
    }
  ],
  "needs_information": [],
  "page": {"next_cursor": null}
}
```

Expose concise trace data to students and retain full trace data for audit/support. Do not reveal internal parser errors or other users' data.

## Validation and error model

Use one error envelope:

```json
{
  "error": {
    "code": "PROFILE_INCOMPLETE",
    "message": "A JEE Main rank is required for this search",
    "fields": [{"path": "profile.exam_results", "code": "MISSING_JEE_RANK"}],
    "request_id": "opaque-id"
  }
}
```

Return `422` for invalid domain input, `401` for missing/invalid authentication, `403` for authorization, `404` without leaking ownership, `409` for revision/idempotency conflicts, `429` for limits, and `503` when a compatible published dataset is unavailable. A zero-result recommendation is a successful `200` with reasons, not a server error.

## Consistency, idempotency, and pagination

- Recommendation POST requests accept an `Idempotency-Key`; bind it to user and canonical request hash.
- Profile PATCH uses an ETag or expected revision to prevent lost updates.
- Pin release and policy versions for the entire run even if publication occurs concurrently.
- Use cursor pagination based on stable rank position and candidate ID. Offset pagination may be used for small static catalog lists.
- Set request timeouts and candidate limits. If future workloads need asynchronous runs, add `202` jobs without changing the engine contract.

## Authentication adapter

Middleware validates provider tokens through a configured adapter and produces the internal principal. Store `(issuer, subject)` rather than relying on an email as identity. Verify issuer, audience, expiry, signature, and authorized party as required by the selected provider. Backend authorization checks resource ownership and roles on every request.

## API security

- Strict CORS allowlist, secure cookies if used, CSRF protection for cookie-authenticated mutations, and rate limits by principal/IP.
- Maximum body and field lengths; reject unknown fields on high-risk admin/extraction schemas.
- Avoid including profile data in URLs, analytics events, exception text, or model prompts.
- Separate public and admin OpenAPI surfaces in production if operationally practical.
- Generate correlation IDs, but never echo sensitive upstream values.

## Compatibility policy

Add fields compatibly within `/v1`; do not repurpose enum meanings. Deprecate with telemetry and a published window. Version domain datasets and decision policies independently from the HTTP API.
