"""A13: what a step knows before any model is asked.

A step cites gestures; those gestures carry recorder.js fingerprints; so the
locator list the protocol wants is built from the cited evidence with no model
involved, in the protocol's own priority order. `origin` is per step, from that
step's own evidence -- in a job spanning two systems the Blue Yonder steps carry
Blue Yonder's origin and the SAP step carries SAP's. A documented
cross-application agent failure is losing window focus during a hand-off, so
data meant for the second application is typed into the first; this is what
stops it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.hosts import system_of
from sro.domain.skill.workflow import Step, Workflow

_UNTARGETED = frozenset({"scroll"})

K_CAUSED_S = 0.5
"""How long after a gesture a call the gesture caused can still start.

A browser dispatches a request from the event handler, so a call the operator
caused starts in the same instant they acted. A page's background traffic runs
on its own timer and lands on whatever gesture happened to be open when it
fired. Measured over every same-origin mutating call in both real stores, the
two populations do not touch:

    every real create   0.016s to 0.059s after its gesture
    every chatter call  0.667s to 8.118s after its gesture

-- 18 real calls under 60ms, 12 chatter calls over 660ms, and nothing between.
The threshold sits an order of magnitude above the slowest real one and still
below the fastest piece of chatter.

It is deliberately generous, because the two mistakes do not cost the same. A
chatter call read as a write makes a run withhold and park a step that changes
nothing -- wasteful. A write read as chatter makes a dry run SEND it. So the
rule only excludes a call it can show was not caused: a call whose start time
the recorder never captured is kept, which is the opposite of `confirming_read`
and for the same reason -- there, "after the write" is the claim being made, so
an untimed call cannot support it; here, "not caused by the gesture" is the
claim, so an untimed call cannot support that either.

ponytail: one constant, no per-host calibration. A page that saves on a
debounce longer than this would look like chatter, and the fix then is the
debounce's own length, not a cleverer rule.
"""

CREATED = 201
"""What a create came back with, on every real one in both stores, and what no
chatter endpoint returned. See `recorded_call`, which prefers such a call over
a sibling on the same step."""

READ_METHODS = ("GET", "HEAD", "OPTIONS")
"""The methods that change nothing. One copy, because "does this step write?"
and "is this the read that confirms the write?" have to be the same question --
`sro.domain.execution.belts` asks it of the same calls this module does."""


@dataclass(frozen=True, slots=True)
class Locator:
    """One rung of the ladder. `within` and `visible_only` are read by the
    extension (`new-chrome-extension/src/background/in-page.js`) to scope and
    filter the match at the wire -- dropping them would let a hidden control
    through."""

    strategy: str
    query: str
    within: str | None = None
    visible_only: bool = True

    def as_payload(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "query": self.query,
            "within": self.within,
            "visible_only": self.visible_only,
        }


def _locator(strategy: str, query: str) -> Locator:
    return Locator(strategy, query)


def locators_for(gesture: Gesture) -> list[Locator]:
    """The ladder, strongest first: the framework's own handle, then role and
    name, then visible text, then the test id, then the css path the protocol
    calls a last resort. A gesture with no target -- a scroll -- has no ladder."""
    target = gesture.action.target
    if target is None:
        return []
    ladder: list[Locator] = []
    component = target.component
    if component is not None:
        query = component.query or (f"#{component.item_id}" if component.item_id else None)
        if query:
            ladder.append(_locator("component", query))
    if target.role and target.name:
        ladder.append(_locator("role_and_name", f"{target.role}|{target.name}"))
    if target.text:
        ladder.append(_locator("text", target.text))
    if target.test_id:
        ladder.append(_locator("test_id", target.test_id))
    if target.css_path:
        ladder.append(_locator("css_path", target.css_path))
    return ladder


def origin_of(gesture: Gesture) -> str | None:
    """Scheme and host of the page the gesture happened on -- else of the first
    call that completed and names a system, else of any call that names one.

    The page first, and this inverts A13's written order on purpose. Every
    consumer of `origin` -- `ui.url`, `screenshot`, the tab `ui.perform` acts
    in -- is about the page the operator was on; `http.send` carries its own
    url and the extension picks a tab from that, so the request host never
    decided the tab. Request-first also had a real failure: a call that never
    completed can be the earliest on a gesture, and a run steered at a dead
    host spends its retries there.
    """
    page = gesture.system or system_of(gesture.url)
    if page:
        return page
    named = [system_of(r.url) for r in gesture.requests]
    completed = [
        s
        for r, s in zip(gesture.requests, named, strict=True)
        if s and r.status is not None and not r.failure_reason
    ]
    if completed:
        return completed[0]
    return next((s for s in named if s), None)


def primary_gesture(step: Step, by_id: Mapping[str, Gesture]) -> Gesture | None:
    """The first cited gesture that exists and can be acted on."""
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is not None and gesture.action.kind not in _UNTARGETED:
            return gesture
    return None


def unperformable(
    workflow: Workflow, by_id: Mapping[str, Gesture], *, from_step: int
) -> Step | None:
    """The first step this job could not be asked to do, or None if it can.

    `primary_gesture`'s question asked of the whole job before it starts, not
    of one step in the middle of it. A step whose every citation is gone or
    untargeted gets no locator, no origin and no plan, so the runner records it
    skipped and stops -- with the steps before it already sent, which leaves a
    warehouse task half performed and a browser open on it.

    Only the steps the run will attempt: the ones before `from_step` were done
    by the operator and are never sent, so evidence they no longer have costs
    this run nothing. Required rather than defaulted to 0 -- a default here is
    a silent "from the beginning" for a caller resuming halfway, which would
    refuse a run over evidence for steps it was never going to attempt.
    """
    for step in sorted(workflow.steps, key=lambda step: step.order):
        if step.order >= from_step and primary_gesture(step, by_id) is None:
            return step
    return None


def _caused_by(gesture: Gesture, call: Call) -> bool:
    """Whether this gesture is what made this call. See `K_CAUSED_S`."""
    if call.started_at is None or gesture.at is None:
        return True
    return abs(call.started_at - gesture.at) <= K_CAUSED_S


def recorded_call(step: Step, by_id: Mapping[str, Gesture]) -> Call | None:
    """The call this step's evidence made: a mutation that came back `CREATED`
    if there is one, else the first mutation, else the first call at all. What
    `http.send` would replay, and what `verify` reads an expected status from.

    Only calls on the gesture's OWN origin. A page's third-party traffic is not
    what the operator did, and reading it as the step's write is what stopped
    every run this repository has ever recorded: step 1 of `new`'s `Create a
    Warehouse Equipment Type` is "Read the equipment type details from an
    email", a click on `mail.google.com`, and the only call it recorded was a
    `POST` to `play.google.com/log` -- Google's telemetry beacon. `writes` read
    that as a mutation, so the run parked for a human approval on a beacon, and
    then `verify` demanded a read-back showing the value the run supplied,
    which a beacon can never show. Six runs, six `stopped`.

    Measured over both real corpora, 719 gestures: of 360 mutating calls, 144
    are cross-origin and every one of them is third-party -- 75 to
    `play.google.com/log`, 44 to assorted `*-pa.clients6.google.com`, 6 from
    the WMS to its sign-in host. So this costs nothing that any operator did.

    **Same origin does not finish the job, and not only on Gmail.** A page's own
    origin makes chatter too, and the warehouse host is no exception -- which an
    earlier draft of this docstring got wrong by counting its mutating calls
    and calling them work. Counted by how many DISTINCT gestures fire each
    same-origin mutating endpoint:

        16  POST mail.google.com/mail/u/*/
        15  POST mail.google.com/sync/u/*/i/s
        14  POST <wms>/refs/data/api/v1/rp/admin/sessionKeepAlive
         9  POST mail.google.com/sync/u/*/i/fd
         8  POST <wms>/data/WM/wm/webPerformanceEntries/batch
         4  POST <wms>/data/WM/wm/customerTypes          <- real
         3  POST <wms>/data/WM/wm/workAreas              <- real
         1  POST <wms>/data/WM/wm/equipmentTypes         <- real

    A session keep-alive and a performance-telemetry batch are POSTs on the
    warehouse's own host, and `recorded_call` returns them. Measured against
    the stored jobs: of 13 steps this classifies as writes, **4 are chatter and
    3 of those 4 are on the WMS** -- `new`'s `Create a Warehouse Equipment
    Type` has its step 5 read as a write by `sessionKeepAlive` and its step 6
    by `webPerformanceEntries/batch`, and both of those steps only type into a
    field. A dry run withholds them, a live run parks them on a person, and
    `verify` asks for a read-back that a keep-alive can never satisfy.

    That table is what `K_CAUSED_S` answers, and frequency is not how. The
    table separates chatter from work everywhere except the 3-to-4 band, where
    `logstreamz` (chatter) sits beside `workAreas` and `workOperations` (real),
    so a threshold on it would be wrong on real jobs. What does separate them
    completely is WHEN the call starts: a write leaves the event handler in the
    same instant the operator acted, and a timer's traffic does not. Of the 13
    steps this used to classify as writes, the 4 chatter ones are now correctly
    not writes, and the 9 that remain are every real create in both stores.

    The response status agrees with that reading, and half of it is safe to act
    on as well. Across both stores every real create came back 201 --
    `customerTypes`, `equipmentTypes`, `workAreas`, `workOperations`,
    `carrierCrossReferences`, `activityCodes` -- and no chatter endpoint ever
    did: `sessionKeepAlive`, `webPerformanceEntries/batch`, Gmail's `sync/u/*`
    and `mail/u/*`, `logstreamz`, `waa` and `perftrace` answer 200 or 204.

    Only half, because the converse does not hold. A real UPDATE returns 200
    too, so "not 201, therefore chatter" would tell a dry run that an edit is
    safe to send unwithheld -- a write must fail safe, and that reading fails
    the wrong way. `writes` is therefore still method-only.

    What IS safe is the preference above: among this step's same-origin
    mutating calls, a 201 is picked over its siblings. It is still a mutation,
    so nothing a dry run withheld stops being withheld, and on the four steps
    that record both -- acme's `Create a Customer Type` steps 1 and 6, its
    `Create an Activity Code` step 7, `new`'s `Create a Customer Type` step 5
    -- it picks the create over the keep-alive by rule rather than by the luck
    of which one the browser happened to fire first.
    """
    reads: list[Call] = []
    mutations: list[Call] = []
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        origin = origin_of(gesture)
        for request in gesture.requests:
            if origin is not None and system_of(request.url) != origin:
                continue
            if not _caused_by(gesture, request):
                continue
            if request.method.upper() not in READ_METHODS:
                mutations.append(request)
            else:
                reads.append(request)
    for request in mutations:
        if request.status == CREATED and not request.failure_reason:
            return request
    if mutations:
        return mutations[0]
    return reads[0] if reads else None


def writes(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    """Whether performing this step changes something. A dry run withholds it."""
    call = recorded_call(step, by_id)
    return call is not None and call.method.upper() not in READ_METHODS


def stood_on(workflow: Workflow, by_id: Mapping[str, Gesture]) -> set[str]:
    """Every system the operator was actually ON while doing this job.

    The tab's origin and the frame's, and nothing else. This is where a plan
    may SEND the browser, and it is the narrower of the two sets on purpose:
    driving somebody's browser somewhere is a different act from replaying a
    call their own click already made.

    `allowlist` is the wider one, and the difference is not hypothetical.
    Measured on this deployment, 2026-09-15: `Create a Customer Type` cites a
    click in Gmail, a Gmail page calls Google's own infrastructure, and so
    `https://play.google.com` was an origin a planner could have navigated an
    operator's browser to -- on the evidence of a telemetry beacon, for a job
    about warehouse customer types. No gesture ever happened there.
    """
    named: set[str] = set()
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None:
                continue
            for candidate in (gesture.system, system_of(gesture.url)):
                if candidate:
                    named.add(candidate)
    return named


def allowlist(workflow: Workflow, by_id: Mapping[str, Gesture]) -> set[str]:
    """Where a call this job's evidence already made may be replayed to.

    `stood_on` plus the origin of every request a cited gesture produced. Those
    origins are here for `recorded_call`: a step's evidence can be a call to an
    API origin the page itself never was -- a form on `wms.example` posting to
    `api.wms.example` -- and `http.send` replays exactly that call. Refusing
    them would refuse the step its own demonstrated write.

    So this is the set for `http.send` alone. What may take the browser
    somewhere is `stood_on`, which is the same question asked about a person
    rather than about a request their page made.
    """
    named = stood_on(workflow, by_id)
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None:
                continue
            for request in gesture.requests:
                system = system_of(request.url)
                if system:
                    named.add(system)
    return named
