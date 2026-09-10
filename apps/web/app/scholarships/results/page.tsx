import type { Metadata } from "next";
import { ResultsExplorer } from "@/components/results";
export const metadata: Metadata = { title: "Scholarship Matches", description: "Review ranked scholarship matches, benefits, deadlines and official sources." };
export default function Page() { return <ResultsExplorer kind="scholarships" />; }
