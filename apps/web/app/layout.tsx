import type { Metadata } from "next";
import { BrandHeader } from "@/components/brand";
import "./globals.css";

export const metadata: Metadata = { title: { default: "ScholarRoute | Find Colleges and Scholarships", template: "%s | ScholarRoute" }, description: "Find suitable colleges and scholarships using verified official information and transparent matching." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><BrandHeader />{children}<footer className="site-footer"><div className="page-shell"><strong>ScholarRoute</strong><span>Official data informs results. Rules determine eligibility. Algorithms rank matches.</span></div></footer></body></html>; }
