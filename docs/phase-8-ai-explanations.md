# Phase 8: Gemini explanation layer

Phase 8 adds optional, student-friendly explanations to ScholarRoute's existing deterministic
results. Gemini never determines eligibility, changes a ranking, recalculates a score, changes a
tier or confidence value, or creates an official link. ScholarRoute remains fully usable when AI
is disabled or unavailable.

## Architecture and data flow

The FastAPI endpoints accept stable persisted identifiers. The server loads the authoritative
ranking or eligibility snapshot, creates a minimal purpose-built context, and sends that context
to `AIExplanationService`. The service uses a replaceable provider abstraction; the production
adapter calls the official Google Gen AI SDK with `gemini-2.5-flash` by default.

Prompts are versioned as `phase8-college-v1`, `phase8-scholarship-v1`, and
`phase8-eligibility-v1`. Database and user-controlled strings are serialized inside an explicitly
untrusted JSON data boundary. The provider is not given web-search tools.

Gemini returns only a strict Pydantic shape containing `summary`, `reasons`, `caveats`, and
`next_steps`. Extra fields are rejected. Scores, tiers, statuses, evidence identifiers, and
official links are copied from ScholarRoute after generation. Generated URLs, admission
probabilities, and admission guarantees are rejected.

## Server configuration

Copy the safe values from `.env.example` into the repository-local ignored `.env` file:

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
AI_ENABLED=false
AI_TIMEOUT_SECONDS=15
AI_MAX_RETRIES=1
AI_MAX_OUTPUT_TOKENS=500
```

Set `GEMINI_API_KEY` only in the backend runtime environment and switch `AI_ENABLED=true` when a
valid key is available. Never use a `NEXT_PUBLIC_` variable for this secret. Production should
inject the key through the hosting platform's secret manager.

Timeouts and retries are intentionally conservative. Only transient timeouts, rate limits, and
provider failures are retried, up to `AI_MAX_RETRIES`. The UI displays a contained unavailable
state while leaving deterministic recommendations, evidence, and official links usable.

## API and local validation

The on-demand endpoints are:

- `POST /api/v1/ai/explain/college`
- `POST /api/v1/ai/explain/scholarship`
- `POST /api/v1/ai/explain/eligibility`

Recommendation requests contain `ranking_run_id` and `rank_position`. Eligibility requests
contain `evaluation_id`. Arbitrary recommendation facts are not accepted from the browser.

Run mocked tests and static checks normally; they never call Gemini or require internet access.
For one live validation, configure the local ignored `.env`, start PostgreSQL and FastAPI using
the existing project instructions, create a deterministic recommendation, and request its
explanation once. Confirm the response is structured and that its `authoritative` and
`official_links` fields exactly match the pre-existing ScholarRoute result. Keep live calls
minimal to protect free-tier quota.

## Privacy and observability

Only the selected result's minimal explanation context is sent to Gemini. Secrets, database
credentials, authorization headers, and unrelated student profile fields are excluded. Logs
record the explanation type, model, prompt version, latency, retry count, and normalized failure
category; they do not record the key or raw prompt.
