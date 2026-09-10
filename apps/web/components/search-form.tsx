"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpenCheck, GraduationCap, LoaderCircle, RotateCcw, SlidersHorizontal, UserRound } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { recommendColleges, recommendScholarships } from "@/lib/api/recommendations";
import { getBranches, getReference, referenceResources, type ReferenceResource } from "@/lib/api/references";
import type { CollegeRequest, ReferenceItem, ScholarshipRequest } from "@/lib/api/types";
import { loadSearch, saveSearch } from "@/lib/search-session";

type Kind = "colleges" | "scholarships";
type Values = Record<string, string | boolean>;
const initial = (): Values => ({ evaluation_year: "", preset: "BALANCED", is_pwd: false, is_ews: false });

function cleanNumber(value: string | boolean) { return value === "" || typeof value === "boolean" ? undefined : Number(value); }
function one(value: string | boolean) { return typeof value === "string" && value ? [value] : []; }

function Field({ label, name, value, onChange, type = "text", placeholder, min, max }: { label: string; name: string; value: string; onChange: (name: string, value: string) => void; type?: string; placeholder?: string; min?: number; max?: number }) {
  return <label className="field"><span>{label}</span><input id={name} name={name} type={type} value={value} min={min} max={max} placeholder={placeholder} onChange={(event) => onChange(name, event.target.value)} /></label>;
}

function SelectField({ label, name, value, options, onChange, placeholder = "Select an option", required = false, disabled = false }: { label: string; name: string; value: string; options: ReferenceItem[]; onChange: (name: string, value: string) => void; placeholder?: string; required?: boolean; disabled?: boolean }) {
  return <label className="field"><span>{label}{required && <b aria-hidden="true"> *</b>}</span><select id={name} name={name} value={value} required={required} disabled={disabled} onChange={(event) => onChange(name, event.target.value)}><option value="">{placeholder}</option>{options.map((item) => <option value={item.code} key={item.id}>{item.name}</option>)}</select></label>;
}

function FormSection({ number, title, helper, icon: Icon, children }: { number: number; title: string; helper: string; icon: typeof UserRound; children: React.ReactNode }) {
  return <section className="form-section"><header><span className="section-number">{number}</span><span className="section-icon"><Icon size={21} aria-hidden="true" /></span><div><h2>{title}</h2><p>{helper}</p></div></header><div className="field-grid">{children}</div></section>;
}

export function SearchForm({ kind }: { kind: Kind }) {
  const router = useRouter();
  const [values, setValues] = useState<Values>(initial);
  const [references, setReferences] = useState<Partial<Record<ReferenceResource, ReferenceItem[]>>>({});
  const [branches, setBranches] = useState<ReferenceItem[]>([]);
  const [loadingRefs, setLoadingRefs] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const college = kind === "colleges";

  useEffect(() => {
    const stored = loadSearch<CollegeRequest | ScholarshipRequest>(kind);
    if (stored) {
      const student = stored.request.student;
      const preferenceValues = kind === "colleges" ? (() => {
        const request = stored.request as CollegeRequest;
        return { preset: request.preset, branch_code: request.branch_code ?? request.preferences.preferred_branch_codes[0] ?? "", preferred_state_code: request.state_code ?? request.preferences.preferred_state_codes[0] ?? "", institution_type_code: request.institution_type_code ?? request.preferences.preferred_institution_type_codes[0] ?? "", maximum_annual_budget: request.preferences.maximum_annual_budget ? String(request.preferences.maximum_annual_budget) : "" };
      })() : (() => {
        const request = stored.request as ScholarshipRequest;
        return { preferred_state_code: request.preferences.preferred_state_codes[0] ?? "", institution_type_code: request.preferences.institution_type_code ?? "" };
      })();
      queueMicrotask(() => setValues((current) => ({ ...current, ...Object.fromEntries(Object.entries(student).map(([key, value]) => [key, typeof value === "boolean" ? value : String(value ?? "")])), ...preferenceValues })));
    }
    Promise.all(referenceResources.map(async (resource) => [resource, (await getReference(resource)).results] as const))
      .then((entries) => {
        const loaded = Object.fromEntries(entries) as Partial<Record<ReferenceResource, ReferenceItem[]>>;
        setReferences(loaded);
        const courseCode = stored?.request.student.target_course_code;
        const course = loaded.courses?.find((item) => item.code === courseCode);
        if (course) void getBranches(course.id).then((page) => setBranches(page.results));
      })
      .catch(() => setError("Reference options could not be loaded. Check the API connection and try again."))
      .finally(() => setLoadingRefs(false));
  }, [kind]);

  const update = (name: string, value: string | boolean) => {
    setValues((current) => ({ ...current, [name]: value }));
    setError("");
    if (name === "target_course_code") {
      setBranches([]);
      setValues((current) => ({ ...current, target_course_code: value, branch_code: "" }));
      const course = references.courses?.find((item) => item.code === value);
      if (course) getBranches(course.id).then((page) => setBranches(page.results)).catch(() => setError("Branches could not be loaded for that course."));
    }
  };
  const options = (resource: ReferenceResource) => references[resource] ?? [];
  const display = useMemo(() => Object.fromEntries(Object.values(references).flat().map((item) => [item.code, item.name])), [references]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!values.evaluation_year || (college && !values.exam_code)) { setError(college ? "Choose an admission year and exam to continue." : "Choose an academic year to continue."); return; }
    setSubmitting(true);
    const student = {
      evaluation_year: Number(values.evaluation_year), exam_code: values.exam_code as string || undefined,
      exam_rank: cleanNumber(values.exam_rank), exam_score: cleanNumber(values.exam_score), exam_percentile: cleanNumber(values.exam_percentile),
      category_code: values.category_code as string || undefined, quota_code: values.quota_code as string || undefined,
      gender_pool_code: values.gender_pool_code as string || undefined, domicile_state_code: values.domicile_state_code as string || undefined,
      board_code: values.board_code as string || undefined, class12_percentage: cleanNumber(values.class12_percentage), family_income: cleanNumber(values.family_income),
      target_course_code: values.target_course_code as string || undefined, institution_type_code: values.institution_type_code as string || undefined,
      is_pwd: Boolean(values.is_pwd), is_ews: Boolean(values.is_ews),
    };
    try {
      if (college) {
        const request: CollegeRequest = { student, preferences: { preferred_branch_codes: one(values.branch_code), alternate_branch_codes: [], preferred_state_codes: one(values.preferred_state_code), preferred_institution_type_codes: one(values.institution_type_code), maximum_annual_budget: cleanNumber(values.maximum_annual_budget) }, preset: values.preset as CollegeRequest["preset"], state_code: values.preferred_state_code as string || undefined, branch_code: values.branch_code as string || undefined, institution_type_code: values.institution_type_code as string || undefined, limit: 10, offset: 0 };
        const response = await recommendColleges(request);
        saveSearch("colleges", { request, response, labels: display });
      } else {
        const request: ScholarshipRequest = { student, preferences: { preferred_benefit_types: [], preferred_state_codes: one(values.preferred_state_code), institution_type_code: values.institution_type_code as string || undefined }, preset: "BALANCED", limit: 10, offset: 0 };
        const response = await recommendScholarships(request);
        saveSearch("scholarships", { request, response, labels: display });
      }
      router.push(`/${kind}/results`);
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "We couldn't submit your search. Please try again."); setSubmitting(false); }
  }

  return <form className={`search-form ${college ? "college-theme" : "scholarship-theme"}`} onSubmit={submit}>
    {loadingRefs && <p className="form-notice" role="status"><LoaderCircle className="spin" size={18} /> Loading official reference options…</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <FormSection number={1} icon={BookOpenCheck} title="Academic details" helper="Your current study and academic performance.">
      <SelectField label={college ? "Admission year" : "Academic year"} name="evaluation_year" value={String(values.evaluation_year ?? "")} options={options("admission-years")} required onChange={update} />
      <SelectField label="Exam" name="exam_code" value={String(values.exam_code ?? "")} options={options("exams")} required={college} onChange={update} />
      {college && <><Field label="Rank / CRL" name="exam_rank" type="number" min={1} value={String(values.exam_rank ?? "")} placeholder="e.g. 12500" onChange={update} /><Field label="Score" name="exam_score" type="number" min={0} value={String(values.exam_score ?? "")} placeholder="Exam score" onChange={update} /><Field label="Percentile" name="exam_percentile" type="number" min={0} max={100} value={String(values.exam_percentile ?? "")} placeholder="0–100" onChange={update} /></>}
      <SelectField label="Board" name="board_code" value={String(values.board_code ?? "")} options={options("boards")} onChange={update} />
      <Field label="Class 12 percentage" name="class12_percentage" type="number" min={0} max={100} value={String(values.class12_percentage ?? "")} placeholder="0–100" onChange={update} />
    </FormSection>
    <FormSection number={2} icon={UserRound} title="Personal & eligibility details" helper="Information used only where official rules require it.">
      <SelectField label="Category" name="category_code" value={String(values.category_code ?? "")} options={options("categories")} onChange={update} />
      <SelectField label="State of domicile" name="domicile_state_code" value={String(values.domicile_state_code ?? "")} options={options("states")} onChange={update} />
      {college && <><SelectField label="Quota" name="quota_code" value={String(values.quota_code ?? "")} options={options("quotas")} onChange={update} /><SelectField label="Gender pool" name="gender_pool_code" value={String(values.gender_pool_code ?? "")} options={options("gender-pools")} onChange={update} /></>}
      {!college && <Field label="Annual family income (₹)" name="family_income" type="number" min={0} value={String(values.family_income ?? "")} placeholder="Annual household income" onChange={update} />}
      <label className="check-field"><input type="checkbox" checked={Boolean(values.is_pwd)} onChange={(event) => update("is_pwd", event.target.checked)} /><span>Person with disability (PwD)</span></label>
      <label className="check-field"><input type="checkbox" checked={Boolean(values.is_ews)} onChange={(event) => update("is_ews", event.target.checked)} /><span>Economically Weaker Section (EWS)</span></label>
    </FormSection>
    <FormSection number={3} icon={SlidersHorizontal} title={college ? "Preferences" : "Scholarship preferences"} helper="Optional choices help rank eligible matches around your priorities.">
      <SelectField label="Course" name="target_course_code" value={String(values.target_course_code ?? "")} options={options("courses")} onChange={update} />
      {college && <SelectField label="Preferred branch" name="branch_code" value={String(values.branch_code ?? "")} options={branches} disabled={!values.target_course_code} placeholder={values.target_course_code ? "Any branch" : "Choose a course first"} onChange={update} />}
      <SelectField label="Preferred state" name="preferred_state_code" value={String(values.preferred_state_code ?? "")} options={options("states")} placeholder="Any state" onChange={update} />
      <SelectField label="Institution type" name="institution_type_code" value={String(values.institution_type_code ?? "")} options={options("institution-types")} placeholder="Any institution type" onChange={update} />
      {college && <><Field label="Maximum annual budget (₹)" name="maximum_annual_budget" type="number" min={0} value={String(values.maximum_annual_budget ?? "")} placeholder="No limit" onChange={update} /><label className="field"><span>Ranking priority</span><select value={String(values.preset)} onChange={(event) => update("preset", event.target.value)}><option value="BALANCED">Balanced match</option><option value="BRANCH_FIRST">Branch first</option><option value="BUDGET_FIRST">Budget first</option><option value="LOCATION_FIRST">Location first</option></select></label></>}
    </FormSection>
    <div className="form-actions"><button type="button" className="button secondary" onClick={() => { setValues(initial()); setBranches([]); setError(""); }}><RotateCcw size={18} /> Reset</button><button type="submit" className={`button primary ${college ? "blue" : "green"}`} disabled={submitting || loadingRefs}>{submitting ? <><LoaderCircle className="spin" size={18} /> Finding matches…</> : <><GraduationCap size={19} /> Find {college ? "Colleges" : "Scholarships"}</>}</button></div>
  </form>;
}
