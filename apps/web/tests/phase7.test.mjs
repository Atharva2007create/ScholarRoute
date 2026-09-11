import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { api, ApiError, safeOfficialUrl } from "../lib/api/client.ts";
import { branchOptionsForExam, courseCodeForExam, engineeringBranches, genderOptions, genderPoolCodeForGender } from "../lib/form-taxonomy.ts";
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

test("forms use references, dependent taxonomy and both clients", async () => {
  const form = await source("components/search-form.tsx");
  assert.match(form, /getReference/); assert.match(form, /branchOptionsForExam/);
  assert.match(form, /recommendColleges/); assert.match(form, /recommendScholarships/);
});

test("exam controls score, course and branch state", async () => {
  const form = await source("components/search-form.tsx");
  assert.match(form, /examCode !== "JEE_MAIN" && <Field label="Score"/);
  assert.match(form, /target_course_code: courseCodeForExam\(String\(value\)\), branch_code: "", exam_score: value === "JEE_MAIN" \? ""/);
  assert.match(form, /disabled placeholder=\{examCode \? "Course set by exam" : "Select an exam first"\}/);
  assert.equal(courseCodeForExam("JEE_MAIN"), "BTECH");
  assert.equal(courseCodeForExam("NEET_UG"), "MBBS");
  assert.deepEqual(branchOptionsForExam("NEET_UG"), []);
});

test("engineering taxonomy is comprehensive, stable and excludes medical specialties", () => {
  const names = new Set(engineeringBranches.map((branch) => branch.name));
  for (const name of ["Computer Science and Engineering", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering", "Electronics and Communication Engineering", "Artificial Intelligence and Machine Learning", "Aerospace Engineering", "Mathematics and Computing"]) assert.equal(names.has(name), true);
  assert.equal(engineeringBranches.length >= 55, true);
  assert.equal(new Set(engineeringBranches.map((branch) => branch.code)).size, engineeringBranches.length);
  for (const specialty of ["Cardiology", "Neurology", "Orthopaedics", "Dermatology", "General Surgery"]) assert.equal(names.has(specialty), false);
});

test("student gender has exactly four choices and derives hidden admission pools", async () => {
  const form = await source("components/search-form.tsx");
  assert.deepEqual(genderOptions.map(({ code, name }) => [code, name]), [["MALE", "Male"], ["FEMALE", "Female"], ["NON_BINARY", "Non-binary"], ["PREFER_NOT_TO_SAY", "Rather not say"]]);
  assert.equal(genderPoolCodeForGender("FEMALE"), "FEMALE_ONLY");
  assert.equal(genderPoolCodeForGender("MALE"), "GENDER_NEUTRAL");
  assert.match(form, /label="Gender" name="gender_code"/);
  assert.doesNotMatch(form, /label="Gender pool"|name="gender_pool_code"/);
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

test("college percentile is a decimal text input with bounded validation", async () => {
  const form = await source("components/search-form.tsx");
  assert.match(form, /label="Percentile" name="exam_percentile" inputMode="decimal" pattern=/);
  assert.doesNotMatch(form, /label="Percentile" name="exam_percentile" type="number"/);
  assert.match(form, /exam_percentile: cleanNumber\(values\.exam_percentile\)/);
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
