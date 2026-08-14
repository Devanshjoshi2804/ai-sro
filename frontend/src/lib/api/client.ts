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

export class ApiError extends Error {
  constructor(readonly problem: Problem) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
  }
}

/**
 * Identity is stubbed to headers in v0, matching the backend. When a real
 * identity provider arrives this is the only place that changes.
 */
function headers(extra?: HeadersInit): HeadersInit {
  return {
    "X-Tenant-Id": env.NEXT_PUBLIC_TENANT_ID,
    "X-Principal-Id": env.NEXT_PUBLIC_PRINCIPAL_ID,
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
    const problem = (await response.json().catch(() => null)) as Problem | null;
    throw new ApiError(
      problem ?? {
        type: "about:blank",
        title: response.statusText,
        status: response.status,
        detail: `${init?.method ?? "GET"} ${path} failed`,
      },
    );
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
  // No Content-Type: the browser sets it with the multipart boundary, and
  // setting it by hand produces a body the server cannot parse.
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};
