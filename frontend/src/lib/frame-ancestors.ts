/**
 * Who may put this console in a frame.
 *
 * Its own module because two very different readers need the same answer:
 * `next.config.ts`, which runs in Node and turns it into a header, and a test
 * that has to be able to ask what the header would say without booting Next.
 */
export function frameAncestors(configured: string | undefined): string {
  const allowed = (configured ?? "")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
  // `'self'` alone when nothing is configured, which forbids every other site
  // -- the console could be framed by anything at all before this existed.
  return ["'self'", ...allowed].join(" ");
}
