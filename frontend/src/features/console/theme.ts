/**
 * The console's palette, now a window onto `brand.css` rather than a second
 * copy of one.
 *
 * These were eighteen hex literals, light-theme, and the only orange in the
 * product that was not the brand's. Twelve files read them through 314 inline
 * `style={{}}` objects, which is why they stay a JS object for now: a `var()`
 * resolves everywhere a hex did, including inside a template literal like
 * `1px solid ${ink.line}`, so the console changes theme without any of those
 * twelve files changing at all. Deleting them for Tailwind classes is its own
 * piece of work.
 */
export const ink = {
  bar: "var(--brand-surface)",
  barText: "var(--brand-strong)",
  barMuted: "var(--brand-muted)",
  page: "var(--brand-ground)",
  panel: "var(--brand-surface)",
  line: "var(--brand-line)",
  lineSoft: "var(--brand-line-soft)",
  text: "var(--brand-heading)",
  textSoft: "var(--brand-body)",
  textMuted: "var(--brand-muted)",
  accent: "var(--brand-accent)",
  accentDeep: "var(--brand-accent-bright)",
  accentWash: "var(--brand-accent-tint)",
  good: "var(--brand-good)",
  goodDot: "var(--brand-good)",
  goodWash: "var(--brand-good-tint)",
  goodLine: "var(--brand-good-line)",
  info: "var(--brand-info)",
  infoWash: "var(--brand-info-tint)",
  danger: "var(--brand-danger)",
  warn: "var(--brand-warn)",
  // A control that cannot be pressed. Light-theme code spelled this as a paler
  // grey than the page; on a dark ground it is a *raised* surface instead, or a
  // disabled button reads as a hole.
  disabled: "var(--brand-raised)",
} as const;

/** Named for the same reason it is loaded at all: a count that changes while
 * you watch it has to stay legible as a count. */
export const mono = "var(--font-mono-face), ui-monospace, SFMono-Regular, monospace";
