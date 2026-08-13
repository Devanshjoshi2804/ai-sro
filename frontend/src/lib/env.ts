import { z } from "zod";

/**
 * Environment, validated once at module load. A missing or malformed variable
 * fails the boot rather than the first request that happens to need it.
 */
const schema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().default("http://localhost:8000"),
  NEXT_PUBLIC_TENANT_ID: z.string().min(1).default("dev"),
  NEXT_PUBLIC_PRINCIPAL_ID: z.string().min(1).default("dev-operator"),
});

export const env = schema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_TENANT_ID: process.env.NEXT_PUBLIC_TENANT_ID,
  NEXT_PUBLIC_PRINCIPAL_ID: process.env.NEXT_PUBLIC_PRINCIPAL_ID,
});
