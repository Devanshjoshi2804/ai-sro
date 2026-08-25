/**
 * The extension origins this console will deal with, and the header that says
 * so.
 *
 * Its own module because two very different readers need the same answer:
 * `next.config.ts`, which runs in Node and turns it into a header, and the
 * credential handoff running in the browser. A test can ask either without
 * booting Next.
 */

/** A bare origin: scheme and host, no path, no trailing slash, nothing else. */
const ORIGIN = /^[a-z][a-z\d+.-]*:\/\/[^/\s;'"]+$/;

/**
 * Configured origins, dropping anything that is not one.
 *
 * Two reasons, and both have teeth. `event.origin` never carries a trailing
 * slash, so `chrome-extension://abc.../` in the allowlist matches nothing and
 * presents as a handshake refused forever with nothing to point at. And this
 * string is spliced into a CSP header: a value containing `;` would append
 * whatever directives it liked to every response the console serves.
 */
export function extensionOrigins(configured: string | undefined): string[] {
  return (configured ?? "")
    .split(",")
    .map((origin) => origin.trim())
    .filter((origin) => ORIGIN.test(origin));
}

export function frameAncestors(configured: string | undefined): string {
  // `'self'` alone when nothing is configured, which forbids every other site
  // -- the console could be framed by anything at all before this existed.
  return ["'self'", ...extensionOrigins(configured)].join(" ");
}
