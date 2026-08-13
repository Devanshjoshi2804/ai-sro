# ADR 005 — One demonstration produces two recipes

**Status:** accepted · v0

## Context

While a clerk clicks, we are recording the network calls their clicks produced.
A capture harness that only records clicks throws that away.

The solution design ranks the capture channels:

```
network calls  >  accessibility tree  >  narration  >  video
```

## Decision

Every step emits up to two independent plans from the same demonstration.

**`network_plan`** — replay of the call the action produced. Fast, robust,
survives UI redesigns, and derived from a human who definitionally did it right.
For Blue Yonder the "network calls" are MOCA commands, so a recording of a wave
release yields a documented, schema-discoverable command sequence rather than a
reverse-engineered guess.

**`ui_plan`** — drive the interface as the human did. The fallback, and the only
option when a call cannot be replayed (CSRF tokens, client-minted signatures,
WebSocket-only flows) or when a step produces no network traffic at all.

A future executor prefers the network plan and falls back to the UI plan. A step
with neither is not a step — `SkillStep` refuses to construct.

**The demo pipeline is an API discovery pipeline.** Built explicitly for that,
not as a side effect.

### Headers are never emitted

A captured request carries cookies, bearer tokens and CSRF headers. Copying them
into a `NetworkPlan` would write live credentials into the skill repository,
where they would be versioned, shared across facilities, and eventually exported.

A skill says *what call to make*. Something else says *how to be allowed to make
it* — auth belongs in the Knowledge Base as a reference to a customer-held
credential.

### Unreplayable plans are kept, not dropped

Document navigations and WebSocket traffic are recorded with `replayable=False`
and a stated reason. They are still the best documentation of what the step did,
and the executor needs to know to skip straight to the UI plan. A plan marked
unreplayable without a reason is refused at construction — an unexplained dead
end is indistinguishable from a capture bug.

## Consequences

- Recipes survive UI redesigns, because the intercepted call outlives the button
  that triggered it.
- Every recording doubles as API documentation for a system whose API was never
  documented.
- Credential handling stays outside the skill repository, which is what makes an
  enterprise security review survivable.
- The executor must implement both paths and a preference between them. Not built
  in v0.
