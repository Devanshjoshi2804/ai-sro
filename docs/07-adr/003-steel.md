# ADR 003 — Steel for browser sessions

**Status:** accepted · v0

## Context

Capture needs a Chrome instance that:

- a human can drive from their own screen while capture runs server-side;
- exposes raw CDP, so `Network.*`, `Accessibility.getFullAXTree` and input events
  can all be subscribed to;
- survives being one of many, and can be reaped when abandoned.

Options were raw Playwright/Puppeteer against a self-managed Chrome pool, or a
browser-infrastructure product.

## Decision

[Steel](https://github.com/steel-dev/steel-browser), self-hosted via Docker.

- Sessions API on `:3000` (mapped to host `:3010` so Next.js keeps `:3000`).
- Raw CDP on `:9223` — Playwright attaches over it, which is what the capture
  adapter needs.
- Built-in session management, live view and request logging.
- Open source and self-hostable, so on-prem WMS deployments are not blocked on a
  SaaS egress path.

The live-view URL is the deciding feature. An operator drives the demonstration
from their own browser while capture happens server-side, and the same surface is
what a later human-takeover queue needs. Building capture around a headless
browser nobody can see would foreclose that.

## Consequences

- One more service in `docker-compose.yml`, needing `shm_size: 2gb` — Chrome
  crashes with Docker's 64 MB default.
- Steel's REST shape is confined to `infrastructure/steel`. The application only
  knows `BrowserProvider`, so replacing Steel is an adapter swap.
- Budget roughly 200–500 MB per session. Browser workers get their own Temporal
  task queue because they are the scarce, stateful, crash-prone resource.
