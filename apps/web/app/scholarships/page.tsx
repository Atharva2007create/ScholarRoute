import type { Metadata } from "next";
import { SearchPage } from "@/components/search-page";
export const metadata: Metadata = { title: "Find Scholarships", description: "Check verified scholarship schemes against your eligibility profile." };
export default function Page() { return <SearchPage kind="scholarships" />; }
