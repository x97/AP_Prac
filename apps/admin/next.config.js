/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1"],
  images: { unoptimized: true },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
      { source: "/assets/:path*", destination: "http://127.0.0.1:8000/assets/:path*" },
    ];
  },
};

module.exports = nextConfig;
