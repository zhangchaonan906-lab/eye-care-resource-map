import { getCorrectionRepository } from "@/lib/corrections/repository";
import { isSameOriginRequest, parseCorrectionInput } from "@/lib/corrections/validation";
import { rateLimitResponse, RATE_LIMITS } from "@/lib/rate-limit/distributed";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function readBoundedBody(request: Request, maximumBytes: number): Promise<string | null> {
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > maximumBytes) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const joined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { joined.set(chunk, offset); offset += chunk.byteLength; }
  return new TextDecoder("utf-8", { fatal: true }).decode(joined);
}

export async function POST(request: Request): Promise<Response> {
  const limited = await rateLimitResponse(request, RATE_LIMITS.correction);
  if (limited) return limited;
  if (!isSameOriginRequest(request)) return Response.json({ data: null, meta: null, error: { code: "ORIGIN_REJECTED", message: "请求校验失败" } }, { status: 403, headers: { "Cache-Control": "no-store" } });
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > 4096) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "提交内容过长" } }, { status: 413 });
  let body: unknown;
  try {
    const raw = await readBoundedBody(request, 4096);
    if (raw === null) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "提交内容过长" } }, { status: 413 });
    body = JSON.parse(raw) as unknown;
  } catch { return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "提交内容格式无效" } }, { status: 400 }); }
  const input = parseCorrectionInput(body);
  if (!input) return Response.json({ data: null, meta: null, error: { code: "INVALID_ARGUMENT", message: "请检查问题类型和说明内容" } }, { status: 400 });
  try {
    const id = await getCorrectionRepository().submit(input);
    return Response.json({ data: { id, status: "pending" }, meta: null, error: null }, { status: 202, headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ data: null, meta: null, error: { code: "SERVICE_UNAVAILABLE", message: "提交暂不可用，请稍后重试" } }, { status: 503, headers: { "Cache-Control": "no-store", "Retry-After": "30" } });
  }
}
