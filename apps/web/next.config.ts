import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  reactStrictMode: true,
  // `npm run typecheck` is the required dedicated type gate; keeping it separate
  // avoids duplicate checker workers during constrained production builds.
  typescript: { ignoreBuildErrors: true },
  experimental: {
    cpus: 1,
    workerThreads: true,
    parallelServerCompiles: false,
    parallelServerBuildTraces: false,
  },
};
export default nextConfig;
