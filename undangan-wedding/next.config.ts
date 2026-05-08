import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for self-hosted deployment via Cloudflare Tunnel + file server
  output: "export",

  // Trailing slash makes static hosting more predictable
  // (each route becomes /route/index.html instead of /route.html)
  trailingSlash: true,

  // Disable Next.js Image optimization since we're exporting static files.
  // Images will be served as-is from /public.
  images: {
    unoptimized: true,
  },

  // Better error messages in dev, harmless in build
  reactStrictMode: true,
};

export default nextConfig;
