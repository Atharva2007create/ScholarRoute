import Link from "next/link";
import { GraduationCap } from "lucide-react";

export function ScholarRouteLogo() {
  return (
    <Link className="brand" href="/" aria-label="ScholarRoute home">
      <span className="brand-mark" aria-hidden="true"><GraduationCap size={30} strokeWidth={2.4} /></span>
      <span><strong>Scholar<span>Route</span></strong><small>Right Information. Brighter Futures.</small></span>
    </Link>
  );
}

export function BrandHeader() {
  return (
    <header className="site-header">
      <div className="page-shell header-inner">
        <ScholarRouteLogo />
        <nav aria-label="Primary navigation">
          <Link href="/colleges">Colleges</Link>
          <Link href="/scholarships">Scholarships</Link>
        </nav>
      </div>
    </header>
  );
}
