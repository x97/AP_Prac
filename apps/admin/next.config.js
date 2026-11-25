/** @type {import('next').NextConfig} */
const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1"],
  images: { unoptimized: true },
  experimental: { agentUpgrade: "security" },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_INTERNAL_URL}/api/:path*` },
      { source: "/assets/:path*", destination: `${API_INTERNAL_URL}/assets/:path*` },
    ];
  },
  async redirects() {
    return [
      { source: "/releases", destination: "/dashboard", permanent: false },
      { source: "/releases/:path*", destination: "/dashboard", permanent: false },
    ];
  },
};

module.exports = nextConfig;
