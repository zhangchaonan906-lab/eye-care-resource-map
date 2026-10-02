export type SecurityHeader = { key: string; value: string };

export function shouldNoIndex(environment: string): boolean {
  return environment === "staging";
}

export function buildSecurityHeaders(environment: string, siteUrl: string): SecurityHeader[] {
  const headers: SecurityHeader[] = [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(self)" },
    { key: "X-Frame-Options", value: "DENY" },
    {
      key: "Content-Security-Policy-Report-Only",
      value: [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "child-src 'self' blob:",
        "frame-ancestors 'none'",
        "form-action 'self'",
      ].join("; "),
    },
  ];

  if (shouldNoIndex(environment)) headers.push({ key: "X-Robots-Tag", value: "noindex, nofollow, noarchive" });

  try {
    if (["staging", "production"].includes(environment) && new URL(siteUrl).protocol === "https:") {
      headers.push({ key: "Strict-Transport-Security", value: "max-age=31536000" });
    }
  } catch {
    // An absent or invalid canonical URL is not evidence that HTTPS is configured.
  }

  return headers;
}

export function validatedSiteUrl(value: string | undefined): URL | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) return undefined;
    return url;
  } catch {
    return undefined;
  }
}
