import { NextResponse } from "next/server";

export const runtime = "nodejs";

/** Server-side only; browser never needs to reach :8000 directly for saves. */
const UPSTREAM_BASE = (
  process.env.INTERNAL_API_BASE_URL ??
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const UPSTREAM_TIMEOUT_MS = Math.min(
  180_000,
  Math.max(5_000, Number(process.env.INTERNAL_API_FETCH_TIMEOUT_MS ?? 75_000)),
);

/**
 * Proxy PUT to FastAPI so the Universe editor uses same-origin fetch (avoids hung browser → :8000 calls).
 */
export async function PUT(request: Request) {
  let body: string;
  try {
    body = await request.text();
  } catch {
    return NextResponse.json({ detail: "Empty or unreadable request body." }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${UPSTREAM_BASE}/api/config/adaptive-rotation`, {
      method: "PUT",
      headers: {
        "Content-Type": request.headers.get("content-type") ?? "application/json",
      },
      body,
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch (cause) {
    const msg = cause instanceof Error ? cause.message : String(cause);
    return NextResponse.json(
      {
        detail: `Backend unreachable (${UPSTREAM_BASE}): ${msg}. From repo root run ./scripts/restart-dev-stack.sh, or set INTERNAL_API_BASE_URL.`,
      },
      { status: 502 },
    );
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
