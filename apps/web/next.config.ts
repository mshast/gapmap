import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: { root: process.cwd() },
  env: {
    NEXT_PUBLIC_GAPMAP_API_URL: process.env.GAPMAP_API_URL ?? "http://127.0.0.1:8000",
  },
  async rewrites() {
    const apiBase = process.env.GAPMAP_API_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
};

export default nextConfig;
