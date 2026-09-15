"""The call a step would send, re-aimed at this run's values.

`plan_step` has always replayed a recorded call byte for byte: the payload it
builds carries `call.request_body.text` and nothing puts the run's values into
it. So a replay of `Create a Customer Type` created the customer type the
DEMONSTRATION created -- `GGD`, every time, whatever the operator asked for.
`value_for` exists and is called only on the `ui.perform` paths.

This is the arithmetic that fixes it, and it is arithmetic rather than a model
because the evidence settles it. Measured on the deployment's own store,
2026-09-15: the three real bodies of that job carry **46 keys each, the same
key set every time, 44 of them byte-identical across all three**, and the two
that differ are the two the operator typed. A body is a constant with slots in
it, and the recording says which are which.

**Two joins, and each catches what the other cannot.**

The first is a diff, and it needs no names. A step cites the gestures that
prove it, and a job demonstrated twice cites both doings -- step 6 of that
workflow cites two gestures, one carrying `"customerType":"GGD"` and the other
`"customerType":"GKB"`. The keys whose values differ between two bodies sent to
the same endpoint are the keys the job varies. Nothing is inferred.

The second decides which of the run's values goes in which slot, and it is the
rule this codebase already applies in two other places -- `network_from_rig._bind`
binds only where "value must be one of the seen values", and `shape.typed_at`
joins a parameter to a gesture through `seen & put_by(gesture)`. A value binds
to a slot only where it is one the operator was seen typing there.

**The name join is refused, and the real body is the counter-example.** A
parameter is named for its control (`control_name`: an ExtJS `itemId`, else the
field label, else the target's name), so it arrives as
`customertype-longDescription` while the body key is `longDescription`. A suffix
match looks obvious and is already ambiguous on the only real body there is: it
carries both `palletBuildingConsolidateBy` (the code the API stores, `""`) and
`displayedPalletBuildingConsolidateBy` (the label the API ignores, `"Inherit
from transport mode"`). A control ending `…ConsolidateBy` matches both, one of
them writes and the other does nothing, and telling them apart needs a
longest-match tiebreak on a correspondence nothing guarantees -- `item_id` is
the page's vocabulary and a body key is the API's. That is a heuristic wearing
arithmetic's clothes.

**Every refusal is a refusal, never a guess.** Ambiguity in either direction, or
a value this run supplied that no key carries, returns `None` -- and the step is
performed through the interface exactly as it is today. The case that makes this
matter is in the ledger's own notes: `csttyp truncates at 4 chars`, and the
captured lifecycle shows a harness asking for `ZV9680` while the body goes out
as `ZV96`. Where the form transformed what was typed, the typed value is not in
the body, nothing binds, and a plan that quietly kept the demonstration's value
would create the demonstration's record again. Refusing sends it to the
interface, where it already works.

**No template machinery.** `network_from_rig._bind` carries a `@@SRO-PARAM-{}@@`
sentinel and `$`-escaping because the skill pipeline must STORE a template and
render it months later, with `absent_as` and `unquoted_as` reconstructing an
absence nobody kept. A run holds the body and the values in one stack frame and
substitutes immediately, so none of that exists here. The rule is borrowed; the
apparatus is not, and `absent_as`/`unquoted_as` must not be imported. The 28
empty strings in that body are structurally unbindable -- `typed_values` drops
an empty string, so no `seen_values` can contain one -- and they go out exactly
as the form sent them, which is what the form sends for a box nobody touched.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from sro.domain.execution.evidence import READ_METHODS, recorded_call
from sro.domain.execution.planning import unreplayable
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.hosts import system_of
from sro.domain.skill.workflow import Step, Workflow


@dataclass(frozen=True, slots=True)
class WritePlan:
    """One call, ready for the wire, with this run's values in it."""

    method: str
    url: str
    body: str | None
    filled: Mapping[str, str]
    """Body key -> the parameter whose value now sits there.

    What the result card reads back. `made_by`'s suffix rule cannot help on this
    endpoint -- the identifier is `customerType`, which ends in none of
    `id`/`code`/`name`/`number`/`key` -- but the plan already knows which keys
    this job varies, so those are the keys worth showing the operator, with
    whatever the warehouse echoed back in them rather than what was sent.
    """

    entry: VerifiedWrite
    """The ledger row this call is proven under. Kept so a reader of the run can
    see which watched endpoint authorised sending bytes instead of clicking."""


def seen_values(workflow: Workflow) -> dict[str, frozenset[str]]:
    """Every value each declared parameter has been observed taking.

    The domain twin of `application.skill.from_rig.bindings_for`, and
    deliberately not shared with it: that one reads a model's raw answer and
    runs safe-naming and collision-dropping over it, while this reads a stored
    `Workflow` whose names already went through exactly that.
    """
    found: dict[str, frozenset[str]] = {}
    for parameter in workflow.parameters:
        name = parameter.get("name")
        raw = parameter.get("seen_values")
        if not isinstance(name, str) or not name or not isinstance(raw, list):
            continue
        values = frozenset(value for value in raw if isinstance(value, str) and value.strip())
        if values:
            found[name] = values
    return found


def _same_endpoint(call: Call, other: Call) -> bool:
    """Whether two calls are the same write, so their bodies may be diffed.

    Method and origin and path. The query is left out for `verified_write_for`'s
    reason: a write does not become a different endpoint because one recording
    carried `?siteId=SG` and the next did not.
    """
    from urllib.parse import urlsplit

    return (
        call.method.upper() == other.method.upper()
        and system_of(call.url) == system_of(other.url)
        and urlsplit(call.url).path == urlsplit(other.url).path
    )


def _bodies_of(step: Step, by_id: Mapping[str, Gesture], like: Call) -> list[dict[str, object]]:
    """Every demonstration of this step's write, as parsed JSON objects.

    One per cited gesture that produced a call to the same endpoint. A job
    demonstrated once yields one, which is the honest answer: with a single
    doing nothing distinguishes a slot from a constant, and the diff below
    returns nothing rather than guessing.
    """
    found: list[dict[str, object]] = []
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for call in gesture.requests:
            if not _same_endpoint(call, like) or unreplayable(call):
                continue
            body = call.request_body
            if body is None or body.text is None:
                continue
            try:
                document = json.loads(body.text)
            except ValueError:
                continue
            if isinstance(document, dict):
                found.append(document)
    return found


def _slots(bodies: list[dict[str, object]]) -> frozenset[str]:
    """The keys the job varies: present in every doing, differing in at least one.

    `present in every doing` matters as much as `differing`. A key one recording
    carried and the next did not is a form that changed between them, not a
    value somebody typed, and substituting into it would send a field the
    demonstration never proved.
    """
    if len(bodies) < 2:
        return frozenset()
    shared = set(bodies[0])
    for body in bodies[1:]:
        shared &= set(body)
    return frozenset(
        key for key in shared if len({json.dumps(body[key], sort_keys=True) for body in bodies}) > 1
    )


def _assigned(
    slots: frozenset[str],
    bodies: list[dict[str, object]],
    values: Mapping[str, str],
    seen: Mapping[str, frozenset[str]],
) -> dict[str, str] | None:
    """Which parameter owns which slot, or None where that is not a fact.

    A parameter claims a slot when every value that slot has been seen taking is
    one the operator was seen typing into that parameter's control. Two
    refusals, both of them silence rather than a guess: a slot two parameters
    claim, and a parameter claiming two slots.
    """
    claimed: dict[str, str] = {}
    for slot in sorted(slots):
        taken = {body[slot] for body in bodies if isinstance(body.get(slot), str)}
        if not taken:
            continue
        owners = [name for name, observed in seen.items() if name in values and taken <= observed]
        if len(owners) > 1:
            return None
        if owners:
            claimed[slot] = owners[0]
    if len(set(claimed.values())) != len(claimed):
        return None
    # Every value this run was given must have somewhere to go. A parameter the
    # operator supplied that no key carries is the transformed-value case, and
    # sending the body without it would send the demonstration's value in its
    # place -- silently, because the endpoint answers 201 either way.
    if any(name not in claimed.values() for name in values):
        return None
    return claimed


def write_plan_for(
    step: Step,
    by_id: Mapping[str, Gesture],
    values: Mapping[str, str],
    verified: tuple[VerifiedWrite, ...],
    seen: Mapping[str, frozenset[str]],
) -> WritePlan | None:
    """The call this step would send with this run's values in it, or None.

    `None` is not a failure. It is this module declining to answer, and every
    caller reads it the same way: perform the step through the interface, which
    is what happens today and what has always happened.
    """
    call = recorded_call(step, by_id)
    if call is None or call.method.upper() in READ_METHODS:
        return None
    if unreplayable(call):
        return None
    entry = verified_write_for(call, verified)
    if entry is None:
        return None
    # A step that types a password is not a step whose body this holds: the
    # recorder struck the value out at the boundary, so there is nothing to
    # substitute and `unreplayable` would already have refused a body carrying
    # the marker. Belt and braces, and cheap.
    if any(
        needs_a_secret(gesture)
        for gesture in (by_id.get(cited) for cited in step.cites)
        if gesture is not None
    ):
        return None

    bodies = _bodies_of(step, by_id, call)
    if not bodies:
        # No JSON body to aim. A form-encoded write is replayable byte for byte
        # and this module has nothing to add to it, so it declines and the
        # existing path sends it as it was recorded.
        return None

    slots = _slots(bodies)
    claimed = _assigned(slots, bodies, values, seen)
    if claimed is None:
        return None

    aimed = dict(bodies[0])
    for slot, parameter in claimed.items():
        aimed[slot] = values[parameter]
    return WritePlan(
        method=call.method.upper(),
        url=call.url,
        body=json.dumps(aimed, ensure_ascii=False),
        filled=dict(claimed),
        entry=entry,
    )


def scaffolding_for(
    workflow: Workflow, by_id: Mapping[str, Gesture], *, write_step: int
) -> tuple[int, ...]:
    """The steps whose only job was to put the write's form on the screen.

    Measured on the deployment's own row: of the six steps of `Create a Customer
    Type`, only step 6 changes warehouse state. Steps 4 and 5 -- typing the code
    and the description -- make no network call at all; they are keystrokes into
    a form that step 6 posts. Step 2's thirty-four GETs are the screen loading.
    Replay the write and there is nothing left for the other five to do.

    Partitioned at the previous write rather than taken from the top, and that
    is what makes it right for a job with more than one write in it: a field
    typed at step 4 whose value leaves in a call fired at step 5 makes step 5 a
    write, so step 4 feeds step 5 and is collapsed only when step 5's own write
    is being replayed too.

    Nothing after the write is scaffolding, and a step that types a password
    never is -- its value was struck out of the evidence, so no replayed body
    can be carrying it.
    """
    from sro.domain.execution.evidence import writes

    ordered = sorted(workflow.steps, key=lambda step: step.order)
    before = [step for step in ordered if step.order < write_step]
    since = 0
    for position, step in enumerate(before):
        if writes(step, by_id):
            since = position + 1
    return tuple(
        step.order
        for step in before[since:]
        if not writes(step, by_id)
        and not any(
            needs_a_secret(gesture)
            for gesture in (by_id.get(cited) for cited in step.cites)
            if gesture is not None
        )
    )
