/**
 * The credential this browser is acting with.
 *
 * Kept in localStorage rather than baked into the build: a token in
 * `NEXT_PUBLIC_*` is one credential shared by everybody who loads the page,
 * which is the same hole as the headers this replaced — every operator would
 * be indistinguishable in the audit trail of a warehouse write.
 *
 * There is no login form yet because there is no user store yet. Somebody with
 * shell access mints a token (`make token tenant=acme principal=you`) and the
 * operator pastes it once.
 */
const KEY = "sro.credential";

let inMemory: string | null = null;

export function credential(): string | null {
  if (inMemory) return inMemory;
  if (typeof window === "undefined") return null;
  inMemory = window.localStorage.getItem(KEY);
  return inMemory;
}

export function remember(token: string): void {
  inMemory = token.trim();
  window.localStorage.setItem(KEY, inMemory);
}

export function forget(): void {
  inMemory = null;
  if (typeof window !== "undefined") window.localStorage.removeItem(KEY);
}

/** What the token says, for showing who is signed in. Never trusted for
 * anything — the backend checks the signature; this only reads the label. */
export function whoAmI(): { tenant: string; principal: string } | null {
  const token = credential();
  const claims = token?.split(".")[1];
  if (!claims) return null;
  try {
    const decoded = JSON.parse(
      atob(claims.replace(/-/g, "+").replace(/_/g, "/")),
    ) as Record<string, unknown>;
    const tenant = typeof decoded.ten === "string" ? decoded.ten : null;
    const principal = typeof decoded.sub === "string" ? decoded.sub : null;
    return tenant && principal ? { tenant, principal } : null;
  } catch {
    return null;
  }
}
