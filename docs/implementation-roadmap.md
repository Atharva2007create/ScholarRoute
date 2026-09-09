# ScholarRoute implementation roadmap

This roadmap stops at planning. Phase 2 starts only after explicit approval and resolution of the listed product decisions.

## Phase 2A: engineering foundation

Deliver the monorepo skeleton, local development environment, FastAPI and Next.js health paths, PostgreSQL migrations, configuration/secrets interfaces, structured logging, CI checks, OpenAPI client generation, and test harnesses.

Exit criteria: reproducible local setup; lint/type/unit checks; migration up/down rehearsal against a disposable database; no business UI beyond a diagnostic shell.

## Phase 2B: one authoritative JEE data slice

Implement the source registry, immutable document metadata, object-storage adapter, JoSAA deterministic parsers for one bounded dataset, canonical mappings, validation findings, release approval records, and atomic publication. Start with fixtures before any scheduled live retrieval.

Exit criteria: a reviewer can trace each published offering/cutoff to a source locator; reruns are idempotent; invalid data cannot reach published queries; rollback succeeds.

## Phase 2C: deterministic college eligibility

Implement the typed profile snapshot, rule AST/compiler, three-state evaluation, rule evidence, boundary test cases, and an application service that produces eligible JEE institution-program offerings for the selected admission year.

Exit criteria: every decision has a stable reason code and rule/source versions; missing data produces `NEEDS_INFORMATION`; historical runs remain reproducible.

## Phase 2D: college ranking and API

Implement historical cutoff bands, preference and budget factors, named ranking presets, traceable score components, recommendation persistence, REST endpoints, ownership checks, idempotency, and generated TypeScript contracts.

Exit criteria: ranking invariants and golden tests pass; no ineligible result is ranked; a result explains its score and caveats without AI.

## Phase 2E: structured student experience

Build the form flow from server-provided catalog choices, accessible validation, results, comparison, data freshness, provenance, and explanation panels. Integrate the selected auth provider through the adapter boundary and add saved profiles/history if included in the MVP.

Exit criteria: keyboard and screen-reader checks; mobile layouts; safe handling of sensitive attributes; full browser flow against a staging release.

## Phase 2F: scholarship vertical

Choose a bounded set of official schemes. Add scholarship cycles, benefits, requirement evidence, scheme rule sets, the `NEEDS_INFORMATION` checklist, ranking policy, official links, and deadline handling.

Exit criteria: scheme criteria are executable and evidence-backed; benefit wording preserves conditions; discovery never implies award approval.

## Phase 2G: NEET/MBBS vertical

Add MCC/NMC reference data, MBBS program/seat models, medical counselling scopes, category/quota mappings, and NEET-specific rules and tests. Add state counselling only authority by authority.

Exit criteria: medical rules do not reuse JEE semantics accidentally; all-India and state scopes are explicit; fixtures cover quota/category boundaries.

## Phase 2H: optional AI explanations and operations

Add Gemini only after deterministic explanations work. Implement data minimization, schema-constrained input/output, grounding validation, cost/latency limits, audit metadata, fallback, and extraction evaluation gates. Complete dashboards, backup/restore drills, retention jobs, incident runbooks, and production readiness review.

Exit criteria: the product remains fully usable when Gemini is unavailable; unsupported generated claims are rejected; recovery and rollback are rehearsed.

## Dependency order

```text
foundation
  -> provenance and release model
  -> one ingestion adapter
  -> published catalog
  -> profile normalization and rule engine
  -> college matching
  -> ranking and recommendation trace
  -> API contracts
  -> student UI/auth
  -> scholarship and NEET verticals
  -> optional Gemini explanations
```

The admin review capability begins with ingestion, not after the student UI. Data accuracy is a product dependency.

## Phase 2 approval checklist

Confirm before implementation:

1. First slice and target admission year. Recommendation: JoSAA/JEE Main, one current cycle plus one historical cycle.
2. MVP counselling scope, including whether state authorities are excluded initially.
3. Definition and disclaimer for historical cutoff bands; no probability forecast is assumed.
4. Named ranking presets and factor priorities, including branch-versus-institution behavior.
5. Whether authentication is mandatory to run a recommendation or only to save one.
6. PostgreSQL, object storage, backend hosting, auth, and email/notification providers.
7. Initial scholarship schemes and whether reminders/application tracking are out of scope.
8. Data reviewer/publisher roles, approval separation, freshness targets, and correction process.
9. Privacy retention period and age/guardian-consent requirements for student accounts.

## Delivery risks and mitigations

| Risk | Impact | Planned response |
|---|---|---|
| Official formats change without notice | Parser failure or incorrect mappings | Immutable fixtures, anomaly checks, source adapters, review gate |
| Admission rules vary by authority/year | False eligibility decisions | Versioned scoped rule sets, precedence validation, evidence, boundary tests |
| Category/quota/gender-pool semantics are conflated | Incorrect seats/cutoffs | Separate controlled dimensions and source aliases |
| “Admission chance” is interpreted as a guarantee | Student harm and trust loss | Historical bands, explicit caveats, no MVP probability claim |
| Missing data becomes a false denial | Lost opportunities | Three-state eligibility and missing-information checklist |
| AI extraction hallucinates fields | Corrupt production data | Schema constraints, evidence locators, validation, human publication |
| Ranking weights encode hidden bias | Unfair or inexplicable ordering | Versioned factors, sensitivity/fairness tests, component disclosure |
| Sensitive student attributes leak | Privacy/security incident | Data minimization, redaction, access controls, retention/deletion, no raw telemetry |
| Year transition mixes datasets | Inconsistent results | Release pinning and one active release per scope/year |
| Broad initial coverage delays correctness | Unusable MVP | One vertical and authority at a time with explicit exit criteria |

## Deliberate exclusions from the MVP

No chatbot, microservices, autonomous web agent, commercial-site scraping, ML admission probability, automatic publication of AI output, arbitrary rule code, vector storage for numerical facts, or Redis without measured justification.
