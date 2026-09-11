"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Building2, CalendarDays, CheckCircle2, CircleAlert, ExternalLink, GraduationCap, IndianRupee, Info, LoaderCircle, MapPin, Search, ShieldCheck, Sparkles } from "lucide-react";
import { ApiError, safeOfficialUrl } from "@/lib/api/client";
import { explainRecommendation } from "@/lib/api/ai";
import { getRecommendation, recommendColleges, recommendScholarships } from "@/lib/api/recommendations";
import type { AIExplanation, CollegeRequest, Recommendation, RecommendationDetail, ScholarshipRequest } from "@/lib/api/types";
import { loadSearch, saveSearch, type StoredSearch } from "@/lib/search-session";
import { fitPercent, humanize } from "@/lib/presentation";
import { selectResultMedia } from "@/lib/media";

type Kind = "colleges" | "scholarships";
const money = (value: string | null) => value ? new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value)) : null;

function Criteria({ stored, kind }: { stored: StoredSearch<CollegeRequest | ScholarshipRequest>; kind: Kind }) {
  const student = stored.request.student;
  const labels = stored.labels;
  const request = stored.request;
  const entries = kind === "colleges" ? [
    ["Exam", student.exam_code], ["Category", student.category_code], ["State", "state_code" in request ? request.state_code : undefined], ["Course", student.target_course_code], ["Quota", student.quota_code],
  ] : [["Category", student.category_code], ["Exam", student.exam_code], ["Domicile", student.domicile_state_code], ["Family income", student.family_income ? money(String(student.family_income)) : undefined], ["Course", student.target_course_code]];
  return <section className="criteria" aria-label="Your search criteria"><strong>Your search criteria</strong><div>{entries.filter(([, value]) => value).map(([label, value]) => <span key={label}><small>{label}</small><b>{labels[String(value)] ?? String(value)}</b></span>)}</div></section>;
}

function MatchBadge({ item }: { item: Recommendation }) {
  return <div className={`match-badge tier-${item.tier.toLowerCase()}`} aria-label={`${fitPercent(item.fit_score)} percent match, ${humanize(item.tier)}`}><Sparkles size={15} aria-hidden="true" /><strong>{fitPercent(item.fit_score)}%</strong><span>{humanize(item.tier)}</span></div>;
}

function MediaFallback({ item, scholarship }: { item: Recommendation; scholarship: boolean }) {
  const initials = (item.organization ?? item.title ?? "ScholarRoute").split(/\s+/).slice(0, 3).map((word) => word[0]).join("").toUpperCase();
  return <div className={`media-fallback ${scholarship ? "green" : "blue"}`} role="img" aria-label={`${item.organization ?? item.title ?? (scholarship ? "Scholarship provider" : "Institution")} logo placeholder`}>{scholarship ? <GraduationCap size={27} /> : <Building2 size={27} />}<strong>{initials}</strong></div>;
}

function ResultMedia({ item, scholarship }: { item: Recommendation; scholarship: boolean }) {
  const [failed, setFailed] = useState(false);
  const media = item.media_verified_at ? selectResultMedia(item, scholarship) : null;
  if (!media || failed) return <MediaFallback item={item} scholarship={scholarship} />;
  const name = item.organization ?? item.title ?? (scholarship ? "Scholarship provider" : "Institution");
  // Dynamic media comes only from backend-verified provenance, so a native image
  // avoids an unsafe wildcard in Next.js remote image configuration.
  // eslint-disable-next-line @next/next/no-img-element
  return <img className={`result-media ${media.kind}`} src={media.url} alt={`${name} ${media.kind}`} loading="lazy" width="224" height="188" referrerPolicy="no-referrer" onError={() => setFailed(true)} />;
}

function OfficialLinks({ links, scholarship }: { links: string[]; scholarship: boolean }) {
  const safe = links.map(safeOfficialUrl).filter((link): link is string => Boolean(link));
  if (!safe.length) return <span className="official-unavailable">Official link unavailable</span>;
  return <div className="official-actions">{safe.slice(0, 2).map((link, index) => <a key={link} href={link} target="_blank" rel="noopener noreferrer" className={index ? "link-secondary" : "official-button"}>{index === 0 ? (scholarship ? "View official page" : "Visit official page") : "More official information"}<ExternalLink size={14} /></a>)}</div>;
}

function ResultCard({ item, kind, onDetails, index }: { item: Recommendation; kind: Kind; onDetails: () => void; index: number }) {
  const scholarship = kind === "scholarships";
  return <article className="result-card" style={{ "--delay": `${Math.min(index, 7) * 45}ms` } as React.CSSProperties}>
    <ResultMedia item={item} scholarship={scholarship} />
    <div className="result-main">
      <div className="result-title-row"><div><p className="result-org">{scholarship ? item.organization : item.title}</p><h2>{scholarship ? item.title : item.organization}</h2></div><MatchBadge item={item} /></div>
      <div className="result-facts">
        {!scholarship && item.state_code && <span><MapPin />{item.state_code}</span>}
        {!scholarship && item.annual_fee && <span><IndianRupee />{money(item.annual_fee)} yearly</span>}
        {scholarship && item.benefit_amount && <span><IndianRupee />Up to {money(item.benefit_amount)}</span>}
        {scholarship && item.deadline && <span><CalendarDays />Deadline {new Date(`${item.deadline}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</span>}
        <span><ShieldCheck />{humanize(item.confidence)}</span>
      </div>
      <p className="result-summary">{item.summary}</p>
      <div className="card-footer"><button type="button" className="details-link" onClick={onDetails}><Info size={15} /> Why this match?</button><OfficialLinks links={item.official_links} scholarship={scholarship} /></div>
    </div>
  </article>;
}

function AIExplanationPanel({ detail, kind }: { detail: RecommendationDetail; kind: Kind }) {
  const [explanation, setExplanation] = useState<AIExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function generate() {
    if (loading) return;
    setLoading(true); setError("");
    try {
      setExplanation(await explainRecommendation(kind === "colleges" ? "college" : "scholarship", detail.ranking_run_id, detail.result.rank_position));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "AI explanation is temporarily unavailable. Your ScholarRoute recommendation is still valid.");
    } finally { setLoading(false); }
  }
  if (!explanation) return <section className="ai-explanation"><div><p className="eyebrow"><Sparkles /> Gemini guidance</p><p>Get a concise explanation grounded only in this ScholarRoute result.</p></div>{error && <p className="ai-error" role="alert">{error}</p>}<button type="button" className="button secondary ai-trigger" onClick={generate} disabled={loading}>{loading ? <><LoaderCircle className="spin" /> Generating explanation…</> : <><Sparkles /> {error ? "Try explanation again" : "Explain this recommendation"}</>}</button></section>;
  return <section className="ai-explanation ai-success"><p className="eyebrow"><Sparkles /> Gemini guidance</p><p>{explanation.explanation.summary}</p><h3>Why it fits</h3><ul>{explanation.explanation.reasons.map((item) => <li key={item}>{item}</li>)}</ul>{explanation.explanation.caveats.length > 0 && <><h3>Keep in mind</h3><ul>{explanation.explanation.caveats.map((item) => <li key={item}>{item}</li>)}</ul></>}<h3>Next steps</h3><ul>{explanation.explanation.next_steps.map((item) => <li key={item}>{item}</li>)}</ul><small>AI wording · Deterministic result unchanged · {explanation.model}</small></section>;
}

function DetailDialog({ detail, loading, kind, onClose }: { detail: RecommendationDetail | null; loading: boolean; kind: Kind; onClose: () => void }) {
  const scholarship = kind === "scholarships";
  return <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}><aside className="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="detail-title"><button autoFocus className="drawer-close" onClick={onClose} aria-label="Close details">×</button>{loading ? <div className="drawer-loading"><LoaderCircle className="spin" /> Loading evidence…</div> : detail && <><p className="eyebrow">Recommendation evidence</p><h2 id="detail-title">Why this match?</h2><p>{detail.result.summary}</p><h3>Match signals</h3><ul className="reason-list">{detail.result.reason_codes.map((reason) => <li key={reason}><CheckCircle2 />{humanize(reason)}</li>)}</ul><h3>Score components</h3><div className="component-list">{detail.result.components.map((component) => <div key={component.name}><span>{humanize(component.name)}</span><strong>{fitPercent(component.score)}%</strong><small>{component.evidence_available ? "Evidence available" : "Limited evidence"}</small></div>)}</div><AIExplanationPanel detail={detail} kind={kind} /><h3>Official evidence</h3><OfficialLinks links={[...detail.result.official_links, ...detail.result.evidence.map((item) => item.official_url ?? "")]} scholarship={scholarship} /></>}</aside></div>;
}

export function ResultsExplorer({ kind }: { kind: Kind }) {
  const [stored, setStored] = useState<StoredSearch<CollegeRequest | ScholarshipRequest> | null>(null);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<RecommendationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  useEffect(() => { queueMicrotask(() => { setStored(loadSearch(kind)); setReady(true); }); }, [kind]);
  useEffect(() => {
    if (!detail) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setDetail(null); };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [detail]);
  const response = stored?.response;
  const page = response ? Math.floor(response.meta.offset / response.meta.limit) + 1 : 1;
  const pages = response ? Math.max(1, Math.ceil(response.meta.total / response.meta.limit)) : 1;

  async function changePage(offset: number) {
    if (!stored) return;
    setLoading(true); setError("");
    try {
      const request = { ...stored.request, offset };
      const next = kind === "colleges" ? await recommendColleges(request as CollegeRequest) : await recommendScholarships(request as ScholarshipRequest);
      const updated = { ...stored, request, response: next } as StoredSearch<CollegeRequest | ScholarshipRequest>;
      saveSearch(kind, updated); setStored(updated); window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "We couldn't load this page of results."); }
    finally { setLoading(false); }
  }
  async function showDetails(item: Recommendation) {
    if (!response) return; setDetailLoading(true); setDetail({ ranking_run_id: response.meta.ranking_run_id, result: item });
    try { setDetail(await getRecommendation(response.meta.ranking_run_id, item.rank_position)); } catch { /* summary detail remains available */ } finally { setDetailLoading(false); }
  }
  const heading = kind === "colleges" ? "Suitable Colleges Found" : "Suitable Scholarships Found";
  const noun = kind === "colleges" ? "colleges" : "scholarships";
  const state = useMemo(() => !response ? "missing" : response.results.length ? "results" : response.meta.needs_information.length ? "needs" : "empty", [response]);

  if (!ready) return <main className="results-page"><div className="page-shell loading-page"><LoaderCircle className="spin" /> Loading your search…</div></main>;
  return <main className={`results-page ${kind === "colleges" ? "college-theme" : "scholarship-theme"}`}>
    <section className="results-hero"><div className="page-shell"><Link href={`/${kind}`} className="back-link"><ArrowLeft size={17} /> Back to search</Link><div className="results-heading"><span><Search /></span><div><h1>{heading}</h1><p>Based on your profile and selected preferences</p></div></div></div></section>
    <div className="page-shell results-shell">
      {stored && <Criteria stored={stored} kind={kind} />}
      {error && <div className="state-card error" role="alert"><CircleAlert /><h2>We couldn’t load your results.</h2><p>{error}</p><button className="button primary blue" onClick={() => changePage(response?.meta.offset ?? 0)}>Retry</button></div>}
      {!error && state === "missing" && <div className="state-card"><Search /><h2>Start a search to see matches</h2><p>Your results stay available only for this browser session.</p><Link className="button primary blue" href={`/${kind}`}>Start search</Link></div>}
      {!error && state === "needs" && <div className="state-card needs"><Info /><h2>We need a little more information</h2><p>Add more academic or eligibility details so the official rules can evaluate additional {noun}.</p><Link className="button primary blue" href={`/${kind}`}>Complete information</Link></div>}
      {!error && state === "empty" && <div className="state-card"><Search /><h2>No suitable {noun} found</h2><p>Modify your search parameters and try again. ScholarRoute does not insert fallback recommendations.</p><Link className="button primary blue" href={`/${kind}`}>Modify search</Link></div>}
      {!error && state === "results" && response && <>
        <div className="results-toolbar"><div><h2>{response.meta.total} matching {noun}</h2><p>{noun.charAt(0).toUpperCase() + noun.slice(1)} are sorted by best match to your profile and preferences.</p></div><label>Sort by <select aria-label="Sort results" disabled><option>Best match</option></select></label></div>
        <div className={`result-grid ${loading ? "is-loading" : ""}`} aria-busy={loading}>{response.results.map((item, index) => <ResultCard key={`${item.subject_id}-${item.rank_position}`} item={item} kind={kind} index={index} onDetails={() => showDetails(item)} />)}</div>
        {pages > 1 && <nav className="pagination" aria-label="Results pages"><button disabled={page <= 1 || loading} onClick={() => changePage(Math.max(0, response.meta.offset - response.meta.limit))}><ArrowLeft /> Previous</button><span>Page {page} of {pages}</span><button disabled={page >= pages || loading} onClick={() => changePage(response.meta.offset + response.meta.limit)}>Next <ArrowRight /></button></nav>}
      </>}
    </div>
    {detail && <DetailDialog detail={detail} loading={detailLoading} kind={kind} onClose={() => setDetail(null)} />}
  </main>;
}
