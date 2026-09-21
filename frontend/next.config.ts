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

  // What the image ships: the server and only the dependencies it traced, not
  // `node_modules` entire. `next start` needs the whole install; this needs
  // `node server.js`. See `frontend/Dockerfile`, and note that it changes
  // nothing about `npm run dev` or `npm run build` locally.
  output: "standalone",

  // Pages that were removed, sent somewhere that answers what they used to.
  // Not a 404: these addresses are in bookmarks, in threads people pasted to
  // each other, and one of them -- `/runs/<id>` -- is still what the
  // extension's panel opens for a run that was not the rig's. Temporary
  // redirects, because the page a question belongs on may move again.
  async redirects() {
    const to = (source: string, destination: string) => ({
      source,
      destination,
      permanent: false,
    });
    return [
      // The job list is now the first half of What we know. A single job and a
      // single run of one keep their addresses: the panel links to both.
      to("/jobs", "/knowledge"),
      // A run is read on its job's page now.
      to("/runs", "/knowledge"),
      to("/runs/:id", "/knowledge"),
      // Teaching in a browser on the server is gone with them.
      to("/recordings", "/knowledge"),
      to("/recordings/:id", "/knowledge"),
      // A run parked for a person is answered in the extension's panel, in the
      // browser that is actually holding the write open.
      to("/needs", "/console"),
      to("/waiting", "/triggers"),
      to("/browsers", "/console"),
      to("/audit", "/overview"),
      to("/spend", "/overview"),
    ];
  },

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
