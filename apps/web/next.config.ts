import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.GAPMAP_NEXT_DIST_DIR ?? ".next",
  turbopack: { root: process.cwd() },
  async rewrites() {
    const apiBase = process.env.GAPMAP_API_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
};

export default nextConfig;
