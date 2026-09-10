import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, BarChart3, CheckCircle2, Compass, DatabaseZap, GraduationCap, ShieldCheck } from "lucide-react";
import { SearchForm } from "./search-form";

export function SearchPage({ kind }: { kind: "colleges" | "scholarships" }) {
  const college = kind === "colleges";
  return <main className={`search-page ${college ? "college-theme" : "scholarship-theme"}`}>
    <section className="search-hero">
      <Image src="/media/scholarroute-campus-hero.png" alt="Indian university campus" fill priority sizes="100vw" />
      <div className="search-hero-wash" />
      <div className="page-shell search-hero-content">
        <Link href="/" className="back-link"><ArrowLeft size={17} /> Back to home</Link>
        <div className="title-row"><span className="title-icon"><GraduationCap size={31} /></span><div><h1>Find {college ? "Colleges" : "Scholarships"}</h1><p>{college ? "Enter your academic and personal details to find the best matching colleges for you." : "Share the details that official schemes use to find relevant scholarship matches."}</p></div></div>
      </div>
    </section>
    <div className="page-shell search-layout">
      <SearchForm kind={kind} />
      <aside className="info-panel" aria-label="How matching works">
        <span className="info-compass"><Compass size={29} /></span>
        <h2>We’ll find the best matches for you</h2>
        <div className="info-rule" />
        <ul>
          <li><ShieldCheck /><span>Based on your profile and preferences</span></li>
          <li><DatabaseZap /><span>Uses verified, available official data</span></li>
          <li><BarChart3 /><span>Preserves eligibility and ranking logic</span></li>
          <li><CheckCircle2 /><span>Shows official sources for each match</span></li>
        </ul>
        <p className="privacy-note">Your details stay in this browser session and are used to request relevant matches.</p>
      </aside>
    </div>
  </main>;
}
