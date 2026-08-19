import { credential, forget } from "@/lib/api/credential";
import { env } from "@/lib/env";
import type { components } from "@/lib/api/generated";

export type Schemas = components["schemas"];

/**
 * The backend answers failures with RFC 9457 problem documents. Carrying the
 * whole document means a screen can show what actually went wrong instead of
 * "request failed".
 */
export type Problem = {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
};

function asText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(asText).join("; ");
  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    const where = Array.isArray(record.loc) ? record.loc.slice(1).join(".") : "";
    const what = typeof record.msg === "string" ? record.msg : JSON.stringify(detail);
    return where ? `${where}: ${what}` : what;
  }
  return detail === undefined || detail === null ? "" : String(detail);
}

export class ApiError extends Error {
  constructor(readonly problem: Problem) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
  }
}

/**
 * Every request carries the operator's own credential. The tenant and the name
 * on a warehouse write come out of that token's signature, not out of a header
 * this code could put anything in.
 */
function headers(extra?: HeadersInit): HeadersInit {
  const token = credential();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.NEXT_PUBLIC_API_URL}${path}`, {
    ...init,
    headers: headers(init?.headers),
    cache: "no-store",
  });

  if (!response.ok) {
    if (response.status === 401) {
      // The token this browser holds is not accepted any more -- expired, or
      // minted by a deployment this is not. Holding on to it leaves the
      // operator clicking a console where nothing works and nothing says why;
      // dropping it puts them back at the paste screen.
      forget();
    }
    const body = (await response.json().catch(() => null)) as Partial<Problem> | null;
    throw new ApiError({
      type: typeof body?.type === "string" ? body.type : "about:blank",
      title: typeof body?.title === "string" ? body.title : response.statusText,
      status: typeof body?.status === "number" ? body.status : response.status,
      // Coerced rather than trusted. An error body is data crossing a trust
      // boundary like any other, and a `detail` that is not a string — a proxy's
      // HTML, a framework's list of validation objects — used to reach React as
      // a child and take the whole page down with it.
      detail: asText(body?.detail) || `${init?.method ?? "GET"} ${path} failed`,
    });
  }

  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  // No Content-Type: the browser sets it with the multipart boundary, and
  // setting it by hand produces a body the server cannot parse.
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};
