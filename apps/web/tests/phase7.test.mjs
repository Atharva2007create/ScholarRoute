import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { api, ApiError, safeOfficialUrl } from "../lib/api/client.ts";
import { fitPercent, humanize } from "../lib/presentation.ts";

const source = (path) => readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("official links allow only HTTP protocols", () => {
  assert.equal(safeOfficialUrl("https://example.edu/apply"), "https://example.edu/apply");
  assert.equal(safeOfficialUrl("javascript:alert(1)"), null);
  assert.equal(safeOfficialUrl("not a url"), null);
});

test("API client sends JSON and returns response data", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (_url, init) => {
    assert.equal(init.headers["Content-Type"], "application/json");
    assert.equal(init.method, "POST");
    return new Response(JSON.stringify({ results: [], meta: { total: 0 } }), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try { assert.deepEqual(await api("/api/v1/recommendations/colleges", { method: "POST", body: "{}" }), { results: [], meta: { total: 0 } }); }
  finally { globalThis.fetch = original; }
});

test("API client converts the Phase 6 error envelope", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "Request validation failed", request_id: "req-1", fields: [] } }), { status: 422, headers: { "Content-Type": "application/json" } });
  try { await assert.rejects(() => api("/bad"), (error) => error instanceof ApiError && error.code === "VALIDATION_ERROR" && error.requestId === "req-1"); }
  finally { globalThis.fetch = original; }
});

test("fit scores are bounded match values", () => {
  assert.equal(fitPercent("92.4"), 92); assert.equal(fitPercent("130"), 100); assert.equal(fitPercent("invalid"), 0);
  assert.equal(humanize("HIGH_CONFIDENCE"), "High Confidence");
});

test("home exposes both journeys and no sample recommendations", async () => {
  const content = `${await source("app/page.tsx")} ${await source("components/home.tsx")}`;
  assert.match(content, /"\/colleges"/); assert.match(content, /"\/scholarships"/);
  assert.doesNotMatch(content, /IIT Delhi|Aarav Sharma|NIT Trichy/);
});

test("forms use references, dependent branches and both clients", async () => {
  const form = await source("components/search-form.tsx");
  assert.match(form, /getReference/); assert.match(form, /getBranches/);
  assert.match(form, /recommendColleges/); assert.match(form, /recommendScholarships/);
});

test("forms omit board and scholarship state preference while preserving domicile", async () => {
  const form = await source("components/search-form.tsx");
  const references = await source("lib/api/references.ts");
  assert.doesNotMatch(form, /label="Board"|board_code:/);
  assert.doesNotMatch(references, /"boards"/);
  assert.match(form, /label="State of domicile"/);
  assert.match(form, /\{college && <SelectField label="Preferred state"/);
  assert.doesNotMatch(form, /ScholarshipRequest = \{[^\n]*preferred_state_codes/);
});

test("results preserve link safety, pagination and needs-information", async () => {
  const results = await source("components/results.tsx");
  assert.match(results, /rel="noopener noreferrer"/); assert.match(results, /needs_information/);
  assert.match(results, /Page \{page\} of \{pages\}/); assert.doesNotMatch(results, /chance of admission/i);
  assert.match(results, /media_verified_at/); assert.match(results, /onError=\{\(\) => setFailed\(true\)\}/);
});

test("responsive and reduced-motion safeguards are defined", async () => {
  const css = await source("app/globals.css");
  assert.match(css, /@media \(max-width: 680px\)/); assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /grid-template-columns: 1fr/);
});
