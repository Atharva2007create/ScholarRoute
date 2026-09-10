import Link from "next/link";
import { ArrowRight, Building2, CheckCircle2, FilePenLine, GraduationCap, SearchCheck } from "lucide-react";

const steps = [["Choose", "Select colleges or scholarships.", SearchCheck], ["Enter details", "Share the information that affects eligibility.", FilePenLine], ["Get results", "Review deterministic, ranked matches.", CheckCircle2], ["Take action", "Continue on verified official pages.", ArrowRight]] as const;

export function ActionCard({ kind }: { kind: "college" | "scholarship" }) {
  const college = kind === "college"; const Icon = college ? Building2 : GraduationCap;
  return <Link href={college ? "/colleges" : "/scholarships"} className={`action-card ${college ? "college" : "scholarship"}`}><span className="action-icon"><Icon size={30} aria-hidden="true" /></span><span className="action-copy"><strong>{college ? "Find Colleges" : "Find Scholarships"}</strong><span>{college ? "Get personalized matches based on your academic profile, preferences and verified data." : "Discover schemes that may match your academic and personal eligibility profile."}</span><small>{college ? "Exams · Preferences · Official data" : "Merit · Need · Official links"}</small></span><span className="action-arrow" aria-hidden="true"><ArrowRight /></span></Link>;
}

export function HowItWorks() {
  return <section className="how-it-works" aria-labelledby="how-title"><div className="how-intro"><p className="eyebrow">A clear route forward</p><h2 id="how-title">How ScholarRoute works</h2></div><ol>{steps.map(([title, copy, Icon], index) => <li key={title}><span className="step-number">{index + 1}</span><Icon size={20} aria-hidden="true" /><div><strong>{title}</strong><p>{copy}</p></div></li>)}</ol></section>;
}
