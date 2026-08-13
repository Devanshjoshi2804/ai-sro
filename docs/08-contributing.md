# Contributing

## Before you start

Read [01-architecture.md](01-architecture.md) and
[02-code-standards.md](02-code-standards.md). Agents read
[../AGENTS.md](../AGENTS.md).

## Branches and commits

`main` is protected. Branch as `type/short-description`:
`feat/recording-list`, `fix/frame-ordering`.

Conventional commits:

```
feat: list recordings by objective
fix: assign frame index in the aggregate, not the caller
docs: add ADR on layered structure
refactor: extract skill version invariants into methods
test: cover derived-parameter ordering
chore: bump ruff
```

Subject in the imperative, under 72 characters. Body says **why**, not what — the
diff already says what.

## Before opening a PR

```bash
make lint     # ruff, ruff format, mypy --strict, import-linter, eslint, tsc
make test     # unit + integration
```

## PR checklist

- [ ] Behaviour change has a test. Bug fix has a test that failed before it.
- [ ] Business rules live on entities, not in use cases.
- [ ] New effect has a port and a fake; new pure calculation has neither.
- [ ] `tenant_id` is in the `WHERE` clause of every new query.
- [ ] No captured request or response body reaches a log or a trace attribute.
- [ ] Domain objects do not cross the HTTP boundary.
- [ ] New vocabulary is in [06-glossary.md](06-glossary.md).
- [ ] Architecture decision has an ADR in [07-adr/](07-adr/).
- [ ] Prose in touched source files is still well under ~25% of lines.
- [ ] Backend schema change → `make types` run and the frontend still builds.
- [ ] The description says what you did **not** do, and why.

## ADRs

Write one when a decision would otherwise be re-argued in six months: a
dependency, a boundary, a rejected alternative, a constraint that shapes the
schema.

Copy [07-adr/000-template.md](07-adr/000-template.md), take the next number.
Never rewrite an accepted ADR — supersede it with a new one and mark the old one
superseded. The record of what we believed *then* is the point.

## Deliberate shortcuts

Mark them where they are, with the ceiling and the upgrade path:

```python
# ponytail: numeric leaves become strings after substitution. Typed
# substitution is a change to render, not to this address scheme.
```

Grep for `ponytail:` to get the ledger.

## Reviewing

- Review the boundary before the implementation. A correct function in the wrong
  layer is the more expensive defect.
- Ask what happens when the WMS is slow, when the browser dies mid-recording, and
  when two tenants do this at once.
- "This is over-engineered" is a valid review comment. So is "this silently
  swallows a failure".
