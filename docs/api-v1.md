# ScholarRoute API v1

Phase 6 exposes the deterministic catalog, eligibility, and recommendation capabilities under
`/api/v1`. Routes accept structured form data only; they do not perform live searches or use AI.

## Endpoints

- `GET /api/v1/reference/{resource}` lists active exams, boards, states, categories, quotas,
  gender pools, institution types, counselling authorities, courses, or admission years.
- `GET /api/v1/reference/branches/by-course/{course_id}` and
  `/programs/by-institution/{institution_id}` support dependent dropdowns.
- `POST /api/v1/eligibility/evaluate` evaluates one program or scholarship cycle with Phase 4.
- `POST /api/v1/recommendations/colleges` discovers eligible programs and ranks them with Phase 5.
- `POST /api/v1/recommendations/scholarships` does the same for current scholarship cycles.
- `GET /api/v1/recommendations/{run_id}/{position}` returns persisted scoring and evidence detail.

Collection routes use bounded `limit` and `offset` values; the default is 20 and the maximum is
100. Recommendation filters narrow canonical data before evaluation. Empty matches return `200`
with an empty `results` array. `NEEDS_INFORMATION` subjects are returned separately in metadata
and never mixed into eligible recommendations.

Errors use `{"error": {"code", "message", "fields", "request_id"}}`. Validation failures return
422, missing resources return 404, database failures return 503, and unexpected details are not
exposed. Every response has `X-Request-ID` correlation. CORS origins are configured with
`SCHOLARROUTE_CORS_ALLOWED_ORIGINS`; wildcard production origins are not enabled.

Run locally with `uvicorn scholarroute.entrypoints.api.app:app --app-dir backend --reload`, then
open `/docs` for Swagger UI or `/openapi.json` for the contract. The current database contains
bounded deterministic fixtures, not a production-scale national catalog.
