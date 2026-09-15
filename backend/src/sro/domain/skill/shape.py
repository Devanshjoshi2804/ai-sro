"""What the extension matches a live tail against.

One entry per proven workflow: its shape -- (system, control identity, kind)
per cited gesture in step order, scrolls left out, the same key `identity.py`
resolves on -- and where in that shape each declared parameter was typed.
Computed from the cited gestures rather than read from `workflow.shape_key`, so
the parameter indices are indices into the very list the extension will walk.

Nothing here carries a typed value. A shape is control identities, hosts and
parameter *names*; the values that went into those controls stay in the
gestures, which is the only place they were ever allowed.

The queries that gather the evidence -- the proven workflows, the held tally,
the cited gestures and this job's own offers -- live in the application layer.
What is left here is the arithmetic: given the pairs and the counsel, the shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

from sro.domain.execution.evidence import primary_gesture, stood_on
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.identity import shape_key, target_identity
from sro.domain.shared.hosts import page_of, system_of
from sro.domain.skill.learned import control_name
from sro.domain.skill.offers import K_OFFER_AFTER, Counsel
from sro.domain.skill.workflow import Step, Workflow, ordered_cites


@dataclass(frozen=True, slots=True)
class Shape:
    id: str
    title: str
    starts_on: str | None
    hosts: list[str]
    shape: list[list[str]]
    parameters: list[dict[str, object]]
    held_runs: int = 0
    offer_after: int = K_OFFER_AFTER
    quiet_until: str | None = None
    """Set when the asking browser refused this job three times running: the
    shape is still served -- the list stays whole and cacheable, and an open
    offer on the job can still tell diverging from finishing -- and
    `recognise.js` declines to offer it until then."""

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def in_time_order(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[Gesture]:
    """The cited gestures in the order they happened.

    **Not step order, and this is the difference between a shape that matches
    and one that cannot.** A shape key is a SEQUENCE of `(system, control,
    kind)`, and `recognise.js` asks whether the operator's last *k* gestures
    ARE this shape's first *k* -- against a tail the browser appends to as
    gestures arrive, which is time order and nothing else. A shape written in
    step order is written in the order the MODEL narrated the job, and a model
    narrates sensibly: "read the request, then create the record". Tenant
    `new`'s `Create a Warehouse Equipment Type` was really done the other way
    round -- the operator opened the WMS form at 16:18:35 and read the mail at
    16:18:46 -- so its step order and its time order disagree, and only one of
    them is what a browser will ever send.

    Measured on both corpora through the real matcher, with the replay fixed to
    feed gestures in time order as a browser does: a step-ordered shape offers
    **3 of acme's 7 jobs and 0 of `new`'s 2**. The same shapes rebuilt in time
    order offer **6 of 7 and 1 of 2**. The missing measurement was in the
    harness -- `dry_run._gestures_of` replayed each job's gestures in step
    order, the same order the shape was built from, so the matcher was being
    handed its own answer.
    """
    # `ordered_cites` and not `cited_ids`: the second is a SET, and a gesture
    # two steps both stand on is two rungs of the key -- dropping the duplicate
    # shortens the shape by one and it stops matching its own job.
    return sorted((by_id[cited] for cited in ordered_cites(workflow) if cited in by_id), key=_when)


def _when(gesture: Gesture) -> tuple[float, str]:
    """Time, then id. `at` is the browser's clock and two gestures of one burst
    can share it, so `at` alone is not a total order -- and a shape that
    permutes between two builds is a shape that stops matching itself."""
    return (gesture.at, gesture.id)


def cited_pairs(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[tuple[Gesture, Step]]:
    """The cited gestures in the order they happened, each still paired with
    the step that cited it. The pairing is what `typed_at` needs and what a
    flat list of gestures throws away.

    Time order and not step order, for the reason `in_time_order` gives: the
    served shape is built from this list, and the tail it is matched against is
    a browser's, which has never heard of a step. `typed_at` reads its index
    out of the same list, so the parameter's position in the shape moves with
    it rather than pointing at whatever now sits where it used to."""
    return sorted(
        (
            (by_id[cited], step)
            for step in sorted(workflow.steps, key=lambda s: s.order)
            for cited in step.cites
            if cited in by_id
        ),
        key=lambda pair: _when(pair[0]),
    )


def put_by(gesture: Gesture) -> set[str]:
    """What this gesture put into the form, as strings a seen value can match.

    Typing carries it in `action.value`. A pick from a dropdown does not. The
    WMS's combo is an ExtJS one: the operator clicks the field, a floating list
    appears, and they click a row of it -- two clicks, neither with a value,
    and what they chose is the clicked row's TEXT. So ten of the forty declared
    parameters across both real stores had no shape index, every one of them a
    dropdown, and an offer could not lift `External System Name` off a live
    tail even where the operator had just picked it.

    Matching the text against the parameter's own `seen_values` is what keeps
    this honest: every click has a label, and "Save" is not a value anybody
    declared. A credential contributes nothing, the rule `typed_values` and the
    tail already wear.
    """
    if gesture.action.secret or (gesture.action.target and gesture.action.target.secret):
        return set()
    found: set[str] = set()
    if gesture.action.value is not None:
        found.add(str(gesture.action.value).strip())
    target = gesture.action.target
    if gesture.action.kind == "click" and target and target.text:
        found.add(target.text.strip())
    return {value for value in found if value}


def typed_at(cited: list[tuple[Gesture, Step]], parameter: dict[str, object]) -> int | None:
    """Where in the shape this parameter was typed, by the step that declares it.

    Scanning every cited gesture for the first value match binds the wrong
    control on any search-then-create flow: the code is typed into the search
    box before it is typed into the field the workflow is actually filling, so
    the extension would fill the search box and stop. Only the step whose
    `parameters` names this one is asked.
    """
    name = str(parameter["name"])
    values = parameter.get("seen_values")
    seen: set[str] = {str(v) for v in values} if isinstance(values, list) else set()
    for index, (gesture, step) in enumerate(cited):
        if name in step.parameters and seen & put_by(gesture):
            return index
    # A parameter learned across doings (`parameters_across`) is recorded on
    # the workflow and on no step: it is named after the control it was typed
    # into, so the control with that name, typing one of its values, is where
    # it sits. Narrower than a value scan -- the search box is not named
    # `workArea` -- and without it every learned parameter had no index and
    # no offer could lift its value from a tail.
    for index, (gesture, _) in enumerate(cited):
        if control_name(gesture) == name and seen & put_by(gesture):
            return index
    return None


def walkable(cited: list[tuple[Gesture, Step]]) -> list[tuple[Gesture, Step]]:
    """The cited pairs the extension can actually match on.

    A scroll is not one: `recognise.js` drops one before it is ever written
    into the tail, so a served shape carrying one could not be matched at any k
    -- a job whose first triple is a scroll could never be offered at all.
    Dropped before both the shape and the parameter indices are computed, so
    `at` indexes the very list the extension walks.
    """
    return [pair for pair in cited if target_identity(pair[0]) != "anon|scroll"]


def shape_of(
    workflow: Workflow, cited: list[tuple[Gesture, Step]], *, held: int, advice: Counsel
) -> Shape | None:
    """One workflow as the extension needs it, or None when it cannot be
    served: nothing cited, a start its own evidence never names, or too short a
    walk to ever be offered."""
    if not cited:
        return None
    gestures = [gesture for gesture, _ in cited]
    by_id = {g.id: g for g in gestures}
    first_step = min(workflow.steps, key=lambda s: s.order)
    first = primary_gesture(first_step, by_id) or gestures[0]
    # The screen, not the visit. What was served here was the whole url of the
    # first gesture of ONE demonstration, so `Create a Customer Type` carried
    # the message id of the mail that operator happened to read, and a WMS job
    # would carry a `libraryContext` session token -- to every browser in the
    # tenant that asks for shapes.
    #
    # Nothing loses anything. Every consumer of this field reduces it to host
    # and path before comparing: `nudge.page` on the way in, `rigArrivals` on
    # what that produced, and `nudge.js` says so in its own docstring -- "the
    # same shape the miner records `starts_on` in", which was not true until
    # now. What NAVIGATES is a different `starts_on` computed in
    # `run_workflow`, and that one still carries the whole url because a
    # warehouse addresses its screens by fragment.
    starts_on = page_of(first.page_url or first.url)
    # Where the operator stood, not everywhere their pages called. `hosts`
    # says which systems this job is done on, and a Gmail page's telemetry
    # beacon is not one of them -- it put `https://play.google.com` on a
    # warehouse job's shape, served to every browser in the tenant.
    hosts = sorted(stood_on(workflow, by_id))
    # `starts_on` is the tab's origin; `hosts` is what the evidence names,
    # which is the frame's. When they disagree the extension would be sent
    # to open an origin no cited gesture ever proved -- so it is not sent.
    if system_of(starts_on) not in hosts:
        return None
    # `starts_on` and `hosts` are read off the whole of the evidence above:
    # where the job begins is a fact about the recording, not about what can
    # be matched.
    walk = walkable(cited)
    # `recognise.js` offers on `shape.slice(0, k)`, and it scans k DOWN FROM
    # `shape.length - 1`: an offer has to leave something to finish, so the
    # whole of a shape is never a prefix anybody is offered. With k at least
    # `K_OFFER_AFTER`, that makes a walk of exactly `K_OFFER_AFTER` positions
    # unmatchable at any k -- served, cached and walked by every browser on
    # every gesture, and unable to fire.
    #
    # This read `< K_OFFER_AFTER` and was off by one against the matcher, which
    # nothing could have caught from this side: the offer replay only ever fed
    # it real mined jobs, all longer. Found by watching a browser do a two-step
    # job over and over with the panel open and nothing ever appearing, and
    # confirmed against `match`'s own loop bound.
    #
    # acme holds shorter rows still: a one-step `Create a Customer Type`, no
    # parameters, whose whole content is "Save the customer type
    # configuration". `validate` refuses to mine such a workflow now, for the
    # neighbouring reason that `resolve` needs `K_MIN_SHARED_STEPS` to dedupe
    # one, but the rows mined before that check are still in the store and
    # there is no way to retire one.
    #
    # `offer_after` below caps at `len(walk) - 1` for the same reason, and that
    # cap is what gives this line its exact form: a shape whose floor exceeds
    # its own cap is one the matcher can never reach.
    if len(walk) <= K_OFFER_AFTER:
        return None
    return Shape(
        id=workflow.id,
        title=workflow.title,
        starts_on=starts_on,
        hosts=hosts,
        shape=[list(triple) for triple in shape_key([g for g, _ in walk])],
        parameters=[
            {"name": str(p["name"]), "at": typed_at(walk, p)}
            for p in workflow.parameters
            if isinstance(p, dict) and p.get("name")
        ],
        held_runs=held,
        # What this job's own offers say: resting on this browser, or offered
        # later. Capped at the last gesture but one, which is as late as
        # `recognise.js` can offer: a job that diverges even there keeps
        # diverging, on record.
        offer_after=max(K_OFFER_AFTER, min(advice.offer_after, len(walk) - 1)),
        quiet_until=advice.quiet_until,
    )
