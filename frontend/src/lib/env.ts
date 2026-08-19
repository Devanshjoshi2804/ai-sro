import { z } from "zod";

/**
 * Environment, validated once at module load. A missing or malformed variable
 * fails the boot rather than the first request that happens to need it.
 */
const schema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().default("http://localhost:8000"),
});

export const env = schema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
});
