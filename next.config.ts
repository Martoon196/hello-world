import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Property Predator / external integrations can post into our API routes,
  // so we keep the body parser permissive and allow large-ish payloads.
  experimental: {},
};

export default nextConfig;
