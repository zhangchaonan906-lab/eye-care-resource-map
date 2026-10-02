import type { MetadataRoute } from "next";
import { shouldNoIndex } from "@/lib/release/security";

export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  if (shouldNoIndex(process.env.APP_ENV ?? "local")) {
    return { rules: { userAgent: "*", disallow: "/" } };
  }
  return { rules: { userAgent: "*", allow: "/" } };
}
