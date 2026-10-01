import { categoriesHandler } from "@/lib/public-api/handlers";

export const runtime = "nodejs";

export function GET(): Promise<Response> {
  return categoriesHandler();
}
