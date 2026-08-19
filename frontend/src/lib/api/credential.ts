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

const listeners = new Set<() => void>();

/** Told whenever the held credential changes, so the gate can re-render.
 *
 * Here rather than in the gate because the gate is no longer the only thing
 * that clears one: a 401 from anywhere means the token this browser holds is
 * not accepted any more, and leaving it in place left the operator clicking a
 * console where nothing worked and nothing said why. */
export function onCredentialChange(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function announce(): void {
  for (const listener of listeners) listener();
}

export function credential(): string | null {
  if (inMemory) return inMemory;
  if (typeof window === "undefined") return null;
  inMemory = window.localStorage.getItem(KEY);
  return inMemory;
}

export function remember(token: string): void {
  inMemory = token.trim();
  window.localStorage.setItem(KEY, inMemory);
  announce();
}

export function forget(): void {
  inMemory = null;
  if (typeof window !== "undefined") window.localStorage.removeItem(KEY);
  announce();
}

/** A credential this browser can still use, or null.
 *
 * Expiry is read here as well as checked by the backend. Nothing did: the gate
 * asked only whether a string existed, so a token that ran out overnight left
 * the console loading normally and failing on every request. */
export function usableCredential(): string | null {
  const token = credential();
  if (!token) return null;
  const expiry = expiresAt(token);
  return expiry !== null && expiry <= Date.now() ? null : token;
}

function expiresAt(token: string): number | null {
  const decoded = claims(token);
  return typeof decoded?.exp === "number" ? decoded.exp * 1000 : null;
}

function claims(token: string): Record<string, unknown> | null {
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/"))) as Record<
      string,
      unknown
    >;
  } catch {
    return null;
  }
}

/** What the token says, for showing who is signed in. Never trusted for
 * anything — the backend checks the signature; this only reads the label. */
export function whoAmI(): { tenant: string; principal: string } | null {
  const token = credential();
  const decoded = token ? claims(token) : null;
  if (!decoded) return null;
  const tenant = typeof decoded.ten === "string" ? decoded.ten : null;
  const principal = typeof decoded.sub === "string" ? decoded.sub : null;
  return tenant && principal ? { tenant, principal } : null;
}
