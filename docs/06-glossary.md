# Glossary

One name per concept. If you need a new term, add it here first.

## Objective key

`domain/shared/objective.py`

The structured identity of a task:

```
{ objective_type, target_system, entity_type, facility, direction }
```

Not a sentence, and never matched by text similarity. Two recordings pair for
induction only if their keys are **exactly** equal; near-misses surface in the
review UI as "these look related, confirm?" rather than being silently diffed.

**Derived, not typed.** The operator starts a demonstration by naming a URL. The
key is read off the evidence when the run is sealed
(`application/capture/identity.py`): the call the demonstration ended on names
the entity and the verb, the query parameter every call carried names the
facility, and the connection the host belongs to names the system. Run 2 is
started under run 1's derived key, so a pair pairs by construction.

Asking for five fields up front is what this replaces. Two people describe one
task two ways, the diff needs exact equality, and the two entry points that
asked disagreed on the default direction — so the same task taught twice
produced two objectives and never paired.

A demonstration that asked the server nothing cannot be named this way, and
sealing it asks the operator instead. That is the exception, not the entry point.

The same task at a different facility is a different objective. It usually is.

## Recording

`domain/recording/recording.py`

One person doing one task once, in a browser we were watching.

| Status | Meaning |
|---|---|
| `capturing` | Live. Frames and artifacts may still arrive. |
| `sealed` | Finished and immutable. Only sealed recordings can be induced. |
| `abandoned` | Ended without usable evidence. Kept, not deleted. |

## Action frame

`domain/recording/events.py`

The normalised unit of a demonstration — one human action plus everything the
page did in response:

```
ActionFrame
├── action        what the human did          (input events)
├── ax_snapshot   what the page looked like   (Accessibility tree, at action time)
└── requests      what the page did about it  (Network domain)
```

That grouping is what makes one demonstration yield two recipes. Lose it and you
have two unrelated logs.

**Primary request** — a click fires analytics beacons, prefetches and one real
mutation. The primary request is the one the frame is actually about: first
successful non-GET, else first successful, else first. A heuristic, kept in one
place so improving it improves every recipe.

## Element fingerprint

`domain/recording/element.py`

A multi-signal description of one element: role, accessible name, text, test id,
CSS path, XPath, tag, attributes.

A single selector is the wrong answer — it breaks on every redesign and leaves
nothing to reason about. Recording several independent signals is what lets a
future heal step score candidates on a changed page.

## Skill

`domain/skill/skill.py`

What was learned from two recordings of the same objective. Identified by its
objective key; versioned append-only.

**Skill version** — steps, parameters, provenance, promotion stage. Steps and
parameters are fixed at induction; only the stage moves.

**Skill step** — an intent plus up to two plans and its assertions.

## Network plan / UI plan

`domain/skill/plan.py`

The two ways to perform a step, both emitted from a single demonstration:

- **network_plan** — replay the call the click produced. Fast, survives UI
  redesigns. Preferred.
- **ui_plan** — drive the interface as a human did. The fallback, and the only
  option for steps with no network signature.

Headers are deliberately never emitted into a network plan. See
[07-adr/005-dual-recipe.md](07-adr/005-dual-recipe.md).

## Parameter

`domain/skill/parameter.py`

A value that varies between runs.

| Kind | Meaning |
|---|---|
| `input` | Supplied by whoever runs the skill. |
| `derived` | Produced by an earlier step's response. Never prompted for. |

Every parameter carries `observed_values` — the two values that proved it varies.
That is the evidence a reviewer reads.

## Site

`application/induction/sites.py`

The precise address of a value inside a step: URL path segment 3, query
parameter `facility`, JSON pointer `/lines/0/qty`, the typed value.

Substitution happens at addresses, never by string replacement, so a quantity of
`3` is never swapped where a page number shares the value.

## Assertion

`domain/skill/assertion.py`

A post-condition, extracted from what the demonstrator checked. Fields identical
across both runs are stable success markers; fields that differed are parameters,
and asserting on those would pin the skill to one run's data.

## Promotion stage

`domain/skill/promotion.py`

`recorded → shadow → assisted → autonomous`. See
[01-architecture.md#promotion-ladder](01-architecture.md#promotion-ladder).

## Induction

`application/induction/`

The process that turns two sealed recordings into a skill version:

```
align → diff and classify → name → extract assertions → emit two plans
```

## Observation

`application/observation/`

What passive capture produces: a continuous stream from an extension in an
operator's own browser, uploaded in **batches**, stored as evidence and mined.
Not a recording — nobody said "watch this", it has no objective key, and it is
not one task. See [ADR 008](07-adr/008-passive-observation.md).

## Episode

`application/observation/segment.py`

A segmented unit of work inside an observation stream: a contiguous run of events
on one host with no idle gap longer than the threshold. Derived, and recomputable
from the batches — a better segmenter is re-run over the same evidence rather
than requiring new evidence.

## Task candidate

`application/observation/mine.py`

An episode *class* seen often enough to propose automating: a signature, its
occurrences, how long each took, and pointers to the episodes that are its
evidence. Teaching a candidate materialises a recording from its best episode and
hands it to induction. A candidate is a proposal to an operator, never something
the system acts on by itself.

## Cross-system workflow

`application/observation/teach.py`, `domain/skill/skill.py`

One skill whose steps call more than one system — "check the WMS, then record the
receipt in the ERP". It is never one task candidate, because an episode breaks on
a host change; it exists only where a person answered `same` to a `workflow`
join, and teaching it builds one demonstration per *occurrence* of the two halves
done in a row. `SkillVersion.systems` names every system it touches, which is
what makes both breakers apply to it and what binds it to a browser: the
deployment holds credentials for one of those systems at most.

Not to be confused with a **Temporal workflow**, which is a durable execution and
has nothing to do with this. Where both could be meant, say "a workflow across
systems" or "the durable workflow".

## Device

`domain/observation/device.py`

One installed extension in one browser profile, registered to a tenant and a
principal. What a command channel addresses, and what a batch was uploaded by.

## Trigger

`domain/trigger/`

What starts a run when nobody typed a sentence: `manual`, `schedule` (cron), or
`inbound` (mail or chat). A trigger for a skill that writes carries the standing
authorisation, named, from the credential of whoever created it — a scheduled
write with nobody's name on it is refused at creation, not at fire time.
