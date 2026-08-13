# ADR 006 — Layers at the top, features inside them

**Status:** accepted · v0

## Context

Two schools disagree about the top-level shape of a codebase.

**Screaming architecture / vertical slice** says a folder listing of `api`,
`models`, `services`, `repositories` communicates nothing about the problem being
solved. Organise by feature, so each slice holds everything it needs.

**Clean / hexagonal architecture** says the dependency rule is the thing worth
protecting, and it is protected by layers.

Both are right about something. The disagreement is about which one goes on the
outside.

## Decision

Layers at the top level, features inside each layer.

```
domain/
  recording/     ← feature
  skill/         ← feature
  shared/
application/
  ports/
  capture/       ← feature
  recording/     ← feature
  induction/     ← feature
  skill/         ← feature
infrastructure/
interface/
```

The reasoning is specific to this product rather than general taste:

**The dependency rule must be mechanically enforceable.** With features on the
outside, "does this feature's persistence code import a browser client?" is a
per-slice review question. With layers on the outside it is four `import-linter`
contracts that run in CI. The systems being automated (MOCA, ION, OData, raw CDP)
are messy and undocumented; the boundary keeping that mess out of the domain has
to be a build failure, not a convention.

**The domain still screams.** `domain/recording/` and `domain/skill/` are the
business, not `models/`. `application/induction/` is a business capability, not
`services/`. Anyone opening `application/` sees capture, recording, induction and
skill — the actual product.

**One bounded context.** Vertical slices pay off most when slices are genuinely
independent. Here everything orbits two aggregates that share a lifecycle: a
recording becomes a skill. Slicing that would duplicate the shared vocabulary
across slices and buy no independence.

The frontend takes the opposite default — feature-sliced — because its slices
*are* independent and its dependency risk is different. See
[04-frontend-walkthrough.md](../04-frontend-walkthrough.md).

## When to revisit

If a second bounded context appears that does not share the recording/skill
lifecycle — a sync layer over WMS event feeds, say, or an anomaly detector —
give it a sibling top-level package with its own layers rather than growing a
feature inside these ones.

That is a module boundary, and it is the point at which vertical slicing starts
paying.

## Consequences

- The dependency rule is a CI failure rather than a review comment.
- Adding a capability touches several directories. Mitigated by
  [03-backend-walkthrough.md](../03-backend-walkthrough.md), which walks the path
  once so nobody has to rediscover it.
- Layer names appear in the tree, which does not scream. Accepted: the layer
  boundary is the one thing here that must never quietly erode.
