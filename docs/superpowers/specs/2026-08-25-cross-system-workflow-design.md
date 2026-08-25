# A workflow across two systems, taught as one skill

"Check the WMS, then record it in the ERP" is one piece of work and can never be
one candidate: an episode breaks on a host change, so the miner sees two. A
model may notice they belong together and say why; a person answers; and this is
what happens after they say yes.

The suggestion and the answer already exist — [`docs/15-observation-to-tasks.md`](../../15-observation-to-tasks.md),
slot 3 and `POST /v1/candidates/{id}/joins`. `docs/15` says merging is not a
thing this does. This spec is the exception it names, and only for the
`workflow` kind: a `variant` answered `same` still dismisses the duplicate,
because two runs of one task are two demonstrations, not two halves.

## What it is

An ordinary skill. Same aggregate, same steps, same promotion ladder, two
additions:

- **`SkillVersion.systems: tuple[str, ...]`** — every host the demonstration
  touched, derived at induction from the assembled frames.

  **On the version, deliberately not on the objective key.** The key is a value
  object compared for equality, and that comparison is what pairs two
  demonstrations of one task. A stray extra host in one occurrence — one call to
  an identity provider, a CDN that answered once — would make two keys unequal
  and the pair would silently never pair, which is the precise failure
  `docs/15` exists to prevent. `target_system` is unchanged: the system of the
  last mutating call, where the job lands.
- **`SkillVersion.crosses_systems`** — a property, `len(systems) > 1`, not a
  stored field. Two pieces of state that can disagree about the same fact is
  one more than is needed. A run of such a version without a `device_id` is
  refused before it starts.

**The breaker is asked about every system in `systems`.** Any one open refuses
the run. This is the field's whole purpose: keyed only where the work lands, a
workflow's writes into the *other* system would be invisible to that system's
breaker, which is the one thing a breaker exists to catch.

Storing it on the version rather than the key has one consequence worth naming:
two versions of one skill could in principle carry different `systems`, because
each is derived from its own demonstrations. That is correct rather than
awkward — it is a true statement about what each version was taught to do, and
the breaker asks the version that is about to run.

**Device-bound by construction.** This deployment stores one session per system
and never holds two at once; the operator's own browser is already signed in to
both. That is not a workaround, it is the reason this became possible at A5/A6.
The cost is stated rather than hidden: **no unattended cross-system runs.** A
trigger may schedule one only by naming a device, and it fires only while that
browser is connected.

## How it is taught

Answering `same` records the fact. Teaching is a separate act, from the same
place the suggestion is shown.

**An occurrence is the unit.** Each time B's episode began within five minutes
of A's ending — the adjacency that produced the suggestion — that pair is one
doing of the whole job. The join only exists because it happened at least twice,
so the two most recent occurrences are the two demonstrations.

**They are diffed as a pair, and never against each other.** The two halves are
sequential parts, not repetitions: diffing the WMS half against the ERP half
would call every difference a parameter and produce a skill that looks richly
parameterised and is nonsense. Occurrence 1 and occurrence 2 are the pair, and
what differs between two doings of the same job is what `induce_skill` already
proves.

**Evidence is read per episode, not per window.** Reading everything between A's
start and B's end is simpler and wrong: the gap can hold five minutes of
unrelated work, and the segmenter has already drawn the boundaries. Each
episode's events come from its own batches by its own timestamps — the existing
`teach.py` machinery — and are concatenated. `assemble_frames` orders them; the
host change is simply where one frame's calls stop.

**The key is derived from the assembled frames**, not handed a candidate's host
as `teach.py` does today — which would name whichever half happened first.
`derive_objective_key` already picks its subject call from the mutations,
intersected with the words on the controls the operator clicked; that call's
host is `target_system`, and every distinct host becomes `systems`.

**The name comes from the model**, over both halves' shapes — the one thing
`docs/15` says a model is unambiguously better at, and neither half's title
describes the job. Nothing about identity rests on it: the objective key is
decided from the evidence before the question is asked, and an empty answer
falls back to the two titles joined.

**Thin evidence degrades, it does not fail.** One usable occurrence means
single-demonstration induction with the reading marked as a model's, exactly as
teaching a candidate does today. None means `needs_demonstration`, and "show me
once" now means demonstrating the whole job in the browser that has both
sessions.

Both candidates are marked `taught` with the same skill id.

## How it runs

**Origin is per step, not per run.** `_origin_of(version)` takes the first step
with a recorded call and `_ui_for` binds the driver to it for the whole run. It
becomes the step's own origin, falling back to the version's for a step with no
call. The extension needs nothing new: `drivenTab(origin)` and `tabOnOrigin(url)`
already pick a tab per origin.

**The credential hazard, and the rule that closes it.** A header plan carries
credential references that name a system — `blue_yonder/SG/cookie` — and
`resolve_headers` fills them from the vault. In a single-system skill every
reference names that system. In a workflow, a step calling the ERP with a header
resolved from the WMS's stored cookie would send one system's live session to
another: silent, credential-shaped, and exactly the kind of thing that is
discovered by somebody else.

*Corrected during implementation.* The rule as written — attach a resolved
header only when its credential names the host being called — was both
unimplementable where it was placed and too narrow. `resolve_headers` has no URL
and no system-to-host map, so it cannot judge that; and the reference on a
header plan is only one of four credential-shaped things keyed to the version's
system. The bearer, the minted CSRF token and the live referer are all looked up
under `session_scope`, which was `<target_system>/<facility>` for every step of
the run. Dropping headers would also leave the second half unauthenticated
rather than merely un-leaked.

**So `session_scope` is decided per call, from the system the call is going to.**
`system_of(connections, url)` after the URL is rendered, falling back to the
skill's own system where nobody has connected that host — `None` means fall
back, never drop, because a device run against a system this deployment holds no
credentials for is the whole point of naming a device. That one move fixes the
bearer, the token and the referer together, and it is the only version in which
the second half can authenticate at all. The header plan's own reference obeys
it too: where the reference names a different system from the calling one, the
calling system's key is used and there is no fall back to the reference — that
would leak the same cookie by the other door. A credential the deployment does
not hold then stops the step with `no live value for …` — except on a device
run, which is every workflow: the browser is the session there, `Cookie` is a
forbidden header for `fetch`, and the resolved value is dropped on the way out
(proved in Chrome). Requiring it refused the one case naming a device exists
for. What still travels from a browser is the bearer, and that is why an
unconnected host in a workflow resolves under its own name instead of falling
back to the skill's.

| Situation | What happens |
|---|---|
| No `device_id` | Refused at start: this skill needs a browser signed in to both |
| No tab on one system | `no_tab_for_origin` → `TargetUnreachable` — a browser that could not be reached, never a skill that drifted |
| Either breaker open | Refused before the first call |
| First half lands, second fails | The steps that ran are recorded and the run is failed — the same as any step-3-of-5 failure |

**A cross-system skill never takes the durable path.** It follows from
device-binding and was unstated: `StartRunRequest` carries no `device_id`, so a
run started by a schedule or a mail relay has no browser, and a version whose
`systems` has two entries is refused before it starts.

**The breaker is written to as well as read from.** `finished_since` filters on
`RunRow.target_system`, so a workflow failing in its ERP half is stored as
`blue_yonder` and would never trip the ERP's breaker — asking every breaker
while answering only one is half a breaker. The run therefore records every
system it touches (`Run.systems`, a JSONB column, migration `0020`), and
`finished_since` matches `target_system == system OR systems @> [system]`.

**There is no rollback.** A workflow that adjusts the WMS and fails to record
the receipt has changed one system and not the other. The run says so. Anything
else would be inventing a transaction across two systems that neither offers.

## Testing

| Asserts | Why |
|---|---|
| A device-less run of a cross-system version is refused | Server-side it would find the second system unauthenticated halfway through a job |
| Two occurrences whose hosts differ slightly still pair | `systems` lives on the version, not in the key that pairing compares |
| An open breaker on *either* system refuses it | The reason `systems` exists |
| Each half of a run resolves its own system's session, and a system this deployment holds no credentials for stops the step rather than borrowing another's | The credential hazard — the first test to write and the last to lose |
| Each step acts in a tab on its own origin | With a per-run origin the ERP half is attempted in the WMS's tab |
| Two occurrences become two recordings, diffed as a pair | That parameters are proven rather than read |
| The two halves are never diffed against each other | The failure that looks like success |
| One usable occurrence degrades to single-demonstration induction | It should get quieter, not fail |
| Both candidates end `taught` with one skill id | Neither is offered again |

Plus one browser test: two systems open, a run that acts in both, and each call
asserted to have gone from the right tab.

**Two things found while implementing this, not caused by it.** A system nobody
has connected is named from its host — `sap.acme.com` derives `acme`, which is
also what somebody is likely to have called their WMS connection. Merged, the
two systems arrive as one name: not a workflow, so no browser required and no
second breaker, and every credential keyed to the first resolved and sent to the
second. `systems_touched` now keeps the host as the name where a derived one
would collide with a connected one. Two hosts of *one* system still merge — a
portal and its API are not two systems, and splitting them would refuse every
ordinary skill for want of a browser.

The second: `ProposeAboutCandidates` returned immediately with no interpreter,
so a deployment without a model got no joins — and therefore no answered
workflow, and therefore no way to reach any of this. The pairing is adjacency in
the evidence and never needed a model; only the sentence did. It now stores the
suggestion either way, with a reason said plainly and `by_model` false.

**What the wire had to say out loud.** `SkillVersionModel.systems` and
`SkillSummary.systems`, because otherwise no screen can tell a workflow from an
ordinary skill until the backend refuses the run: the console's card asks which
browser before offering the button, and the trigger board refuses to make a
schedule that would be refused at every fire.

## Deliberately not here

- **Rollback or compensation** — see above.
- **More than two systems.** `systems` is a tuple and the code would not care,
  but join detection only ever pairs two candidates. A three-system job is two
  joins and nothing can teach it yet.
- **Cross-system runs with no browser at all** — follows from device-binding.
  A schedule *may* point a workflow at a connected browser (the trigger board
  requires one, and sends `medium: network`, because the steps are calls and
  what the browser is for is the session each system's tab already holds). What
  cannot happen is the durable path: `StartRunRequest` carries no `device_id`,
  so a workflow fired with nothing named is refused before it starts.
- **Reordering or editing merged steps.** The frames come out in the order they
  happened; a screen for rearranging a taught workflow is a bigger feature than
  this one.
- **Merging variants into one skill.** A `variant` answered `same` still
  dismisses the duplicate. Two runs of one task are already what the two-run
  diff is for, and using them as one skill's two demonstrations is a separate
  improvement worth its own design — it would help *every* candidate, not only
  joined ones.
