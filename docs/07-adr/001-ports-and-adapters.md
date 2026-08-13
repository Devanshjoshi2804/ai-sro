# ADR 001 — Ports and adapters, enforced by import-linter

**Status:** accepted · v0

## Context

The systems this platform automates are not knowable in advance. Blue Yonder is
MOCA on-prem at one site and Luminate REST at another. Infor's throttling limits
are per-endpoint and undocumented. Some steps have no API at all.

Every one of those is an integration that will be written *after* the domain
logic, against a system we cannot test locally.

A conventional layered structure would work until the first deadline, at which
point a repository would import a Steel client "just for now".

## Decision

Four layers with dependencies pointing inward, and the rule enforced mechanically
by four `import-linter` contracts in `backend/pyproject.toml`:

1. Layers point inward only.
2. `domain` imports nothing else in the codebase, and no framework.
3. `application` imports abstractions, never adapters.
4. `interface` cannot import `infrastructure`.

`sro.container` is the composition root and the only module that imports
`infrastructure`.

Rejected: relying on review to enforce it. Layering that is not checked is a
diagram, not an architecture.

Rejected: a DI framework. Constructor injection wired in one file is enough at
this size and needs no runtime magic.

## Consequences

- The whole application layer tests against in-memory fakes. `make test-unit`
  needs no Docker and runs in under a second.
- Swapping Postgres, Steel or MinIO is an adapter change with no reach into
  business logic.
- Some indirection that looks unnecessary today: a `Clock` port instead of
  `datetime.now()`. That one is what makes every timestamp in tests deterministic.
- New effects require a port, which is friction by design. The rules for when a
  port is *not* warranted are in
  [02-code-standards.md#ports](../02-code-standards.md#ports).
