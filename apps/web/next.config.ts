import type { NextConfig } from "next";
import { buildSecurityHeaders } from "./src/lib/release/security";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    const securityHeaders = buildSecurityHeaders(process.env.APP_ENV ?? "local", process.env.SITE_URL ?? "");
    return [{
      source: "/:path*",
      headers: securityHeaders,
    }, {
      source: "/admin/:path*",
      headers: [...securityHeaders, { key: "Cache-Control", value: "no-store" }],
    }, {
      source: "/api/admin/:path*",
      headers: [...securityHeaders, { key: "Cache-Control", value: "no-store" }],
    }];
  },
};

export default nextConfig;
