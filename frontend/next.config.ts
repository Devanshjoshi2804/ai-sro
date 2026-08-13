import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Agent instructions live in the repo root AGENTS.md, which CLAUDE.md points
  // at. Next regenerates its own copies here otherwise, and two sets of rules
  // drift apart immediately.
  agentRules: false,
};

export default nextConfig;
