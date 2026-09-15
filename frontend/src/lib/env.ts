import { z } from "zod";

/**
 * Environment, validated once at module load. A missing or malformed variable
 * fails the boot rather than the first request that happens to need it.
 */
const schema = z.object({
  /** Absolute (`http://host:8000`) or same-origin (`/api`).
   *
   * Same-origin is what a reverse proxy in front of both makes possible, and
   * it is the only way one console image serves more than one environment:
   * Next inlines this at build time, so an absolute url here is a promise
   * about a hostname baked into the bundle. A path is a promise about
   * nothing. */
  NEXT_PUBLIC_API_URL: z
    .string()
    .refine((value) => value.startsWith("/") || URL.canParse(value), {
      message: "must be an absolute url or a path beginning with /",
    })
    .default("http://localhost:8000"),

  /** Extension origins allowed to hand this console a credential, and to frame
   * it. Comma-separated `chrome-extension://<id>`; empty means neither. */
  NEXT_PUBLIC_EXTENSION_ORIGINS: z.string().default(""),
});

export const env = schema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  // Named literally, not spread: Next inlines `process.env.NEXT_PUBLIC_*` only
  // where it appears verbatim, so a spread reaches the browser as undefined.
  NEXT_PUBLIC_EXTENSION_ORIGINS: process.env.NEXT_PUBLIC_EXTENSION_ORIGINS,
});
