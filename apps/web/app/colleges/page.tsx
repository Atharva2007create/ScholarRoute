import type { Metadata } from "next";
import { SearchPage } from "@/components/search-page";
export const metadata: Metadata = { title: "Find Colleges", description: "Enter your profile and preferences to find suitable college programs." };
export default function Page() { return <SearchPage kind="colleges" />; }
