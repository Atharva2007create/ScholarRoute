# ScholarRoute recommendation engines

## Shared outcome model

Eligibility uses three states:

- `ELIGIBLE`: all mandatory rules pass.
- `INELIGIBLE`: at least one conclusive mandatory rule fails.
- `NEEDS_INFORMATION`: no rule conclusively fails, but required profile data or evidence is missing.

Each evaluation returns stable reason codes, rule versions, observed inputs, source evidence, and a short deterministic explanation. An engine must distinguish “no rule applies” from “rule data is unavailable.”

## Rule representation and execution

Rules are data, but the rule language remains constrained and typed. Store a validated abstract syntax tree in JSONB, for example:

```json
{
  "op": "all",
  "args": [
    {"op": "lte", "field": "profile.household_income", "value": 800000, "unit": "INR/year"},
    {"op": "in", "field": "profile.domicile_state", "values": ["MH"]},
    {"op": "gte", "field": "profile.board_percentage", "value": 75, "unit": "percent"}
  ]
}
```

Allowed operators are explicit. Fields come from a versioned fact catalog with types and null behavior. Compile the AST to in-process predicates for the MVP; use SQL only for coarse candidate preselection. Never evaluate source-provided code, Python, templates, or arbitrary SQL.

Rules form sets scoped by authority, year, scheme/cycle, offering taxonomy, quota, category, or gender pool. Precedence must be explicit: more-specific rules can refine a general rule but cannot silently replace it. Conflicting applicable rules fail closed into review/operational error, not student ineligibility.

## Eligibility engine

Inputs are an immutable normalized profile snapshot, candidate facts, a rule-set version, and an evaluation date. Output is a decision plus ordered predicate traces.

Evaluation order may short-circuit internally for performance, but the engine should report all material failures that help the student. Rules cover exam/rank presence, board thresholds, subject requirements, domicile, quota/category, gender pool, age where official, income, credentials, and application dates.

Historical cutoff position is not base eligibility unless the governing authority explicitly makes it one. A student outside a prior closing rank can still be shown as an eligible but lower-confidence/higher-reach option.

## College matching

1. Select offerings for the pinned admission cycle and requested course scope.
2. Apply explicit hard preferences only when the user marks them required. Soft location, branch, institution, and budget preferences must not remove otherwise eligible options.
3. Run deterministic eligibility for each remaining offering.
4. Enrich eligible candidates with fee, location, quality signals, and comparable historical cutoff observations.
5. Label missing/stale data and pass candidates to ranking.

Return institution and program separately. A recommendation is for a concrete institution-program-offering in an admission cycle, not for an institution name alone.

## Scholarship matching

1. Select open or upcoming scholarship cycles relevant to the intended course/year/state.
2. Evaluate scheme rules against the profile and declared credentials.
3. Separate `ELIGIBLE` from `NEEDS_INFORMATION`; list the missing attributes or documents for the latter.
4. Calculate benefit comparability only when units and periods align. Preserve “up to,” conditional, reimbursement, waiver, and recurring semantics.
5. Rank eligible schemes and show application windows, benefit, required documents, and official application source.

Do not claim that a student “will receive” a scholarship. The result means the known profile satisfies published screening rules; the provider makes the award decision.

## Ranking engine

Eligibility is a gate. Ranking never turns an ineligible item into a recommendation.

Use versioned, named policies. A policy defines factors, direction, normalization, missing-data behavior, weight ranges, and tie-breaking. Suggested MVP college factors:

- historical cutoff margin/band for the student's applicable pool;
- branch preference fit;
- location preference fit;
- budget fit using comparable annual cost;
- separately displayed official quality signals.

Suggested scholarship factors include benefit fit, academic/profile alignment beyond the mandatory threshold, application-window urgency, and evidence completeness. Do not use sensitive protected attributes as quality signals; use them only where an official eligibility rule requires them.

Avoid a false-precision “admission probability” in the MVP. Classify historical position as `LIKELY_RANGE`, `COMPETITIVE_RANGE`, `REACH_RANGE`, or `NO_COMPARABLE_HISTORY` using an approved method, while stating that past cutoffs do not guarantee outcomes.

For each result return:

```text
total score
policy/version
factor raw values
normalization method
weights and contributions
missing-data penalties or neutral handling
deterministic tie-break reason
```

Run sensitivity tests so small input changes near thresholds do not cause unexplained large rank changes. A new policy version never alters the reproducibility of an old run.

## Explanation layer

Generate a complete template explanation from trace data first. Optional Gemini input is a minimized JSON object containing only approved statements, such as passed requirements, preference matches, score factors, caveats, and source labels. Require structured output and verify that all claims map to supplied facts. On timeout, schema failure, or unsupported claims, return the template explanation.

Never send names, email addresses, document images, auth tokens, or unnecessary sensitive attributes to Gemini. The explanation endpoint must not call ingestion tools or retrieve arbitrary web content.

## Reproducibility example

A recommendation response should identify:

```text
recommendation_run_id
profile_snapshot_hash
catalog_release_id
rule_set_versions
ranking_policy_version
evaluation_timestamp
candidate decision traces
source document version references
```

This allows support staff to reconstruct why the system showed an option even after the next admission-year release is published.

## Tests

- Table-driven unit tests for every rule operator and three-state null behavior.
- Authority-provided examples and reviewer-authored boundary cases for each rule set.
- Property tests around thresholds, rank boundaries, dates, and set membership.
- Golden recommendation tests pinning catalog, rules, and policy versions.
- Ranking invariants: ineligible candidates absent, weights valid, deterministic ties, monotonic behavior where intended.
- Metamorphic/fairness checks: changing an irrelevant attribute must not change eligibility or score.
- Explanation grounding tests: every sentence maps to a trace fact; fallback works without Gemini.
- Load tests using realistic candidate counts and worst-case rule sets.
