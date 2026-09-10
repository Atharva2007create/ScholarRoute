"use client";
import { CircleAlert } from "lucide-react";
export default function ErrorBoundary({ reset }: { error: Error & { digest?: string }; reset: () => void }) { return <main className="error-boundary"><CircleAlert size={44} /><h1>Something went wrong</h1><p>This page could not be displayed. Your search details remain in this browser session.</p><button className="button primary blue" onClick={reset}>Try again</button></main>; }
