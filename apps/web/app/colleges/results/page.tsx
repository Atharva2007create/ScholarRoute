import type { Metadata } from "next";
import { ResultsExplorer } from "@/components/results";
export const metadata: Metadata = { title: "College Matches", description: "Review ranked college matches and verified official pages." };
export default function Page() { return <ResultsExplorer kind="colleges" />; }
