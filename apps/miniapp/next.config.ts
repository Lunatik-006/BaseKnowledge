import type { NextConfig } from "next";
import "./lib/logger";
console.info("Miniapp config loaded");

const nextConfig: NextConfig = {
  // Expose PUBLIC_URL to the client bundle so client-side code can read it
  env: {
    PUBLIC_URL: process.env.PUBLIC_URL,
  },
};

export default nextConfig;
