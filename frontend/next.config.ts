import type { NextConfig } from "next";
import { frameAncestors } from "./src/lib/frame-ancestors";

// Read from the environment here rather than through `lib/env.ts`: this file
// runs in Node at build and boot, and that module exists to get values into the
// browser bundle. Same variable, two readers, on purpose.

const nextConfig: NextConfig = {
  // Agent instructions live in the repo root AGENTS.md, which CLAUDE.md points
  // at. Next regenerates its own copies here otherwise, and two sets of rules
  // drift apart immediately.
  agentRules: false,

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            // Without this, any site may frame the console -- which is worth
            // closing whether or not the extension's panel is in use here. With
            // nothing configured this is `'self'` alone, so the default is that
            // nobody else may.
            key: "Content-Security-Policy",
            value: `frame-ancestors ${frameAncestors(process.env.NEXT_PUBLIC_EXTENSION_ORIGINS)}`,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
