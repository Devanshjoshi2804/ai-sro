# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See [AGENTS.md](AGENTS.md).

This project follows the AGENTS.md open standard. All agent-facing instructions
live in that one file so they cannot drift between tools. Add nothing here that
is not Claude-specific — put it in `AGENTS.md`.

Note: `frontend/next.config.ts` sets `agentRules: false`. Next.js otherwise
generates its own `frontend/AGENTS.md` and `frontend/CLAUDE.md`, which is exactly
the drift this arrangement exists to prevent.
