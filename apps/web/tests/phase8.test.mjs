import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("explanation client uses stable identifiers and the Phase 6 error-aware client", async () => {
  const client = await source("lib/api/ai.ts");
  assert.match(client, /api<AIExplanation>/);
  assert.match(client, /ranking_run_id: rankingRunId/);
  assert.match(client, /rank_position: rankPosition/);
  assert.match(client, /\/api\/v1\/ai\/explain\/\$\{kind\}/);
});

test("result drawer keeps deterministic evidence and adds complete AI states", async () => {
  const results = await source("components/results.tsx");
  assert.match(results, /Explain this recommendation/);
  assert.match(results, /Generating explanation/);
  assert.match(results, /explanation\.explanation\.reasons/);
  assert.match(results, /explanation\.explanation\.caveats/);
  assert.match(results, /explanation\.explanation\.next_steps/);
  assert.match(results, /recommendation is still valid/);
  assert.match(results, /Deterministic result unchanged/);
  assert.match(results, /detail\.result\.official_links/);
});

test("ordinary rendering does not automatically request Gemini", async () => {
  const results = await source("components/results.tsx");
  assert.match(results, /onClick=\{generate\}/);
  assert.doesNotMatch(results, /useEffect\([^]*explainRecommendation/);
});
