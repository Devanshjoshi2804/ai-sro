"""A9, A10 — the only code here that overrules a model.

`validate` reads no URL, no body and no call shape. It asks whether a workflow
has any steps at all, whether every step cites something, whether everything
cited exists, whether every step says something a person could act on, and
whether every system named -- by a step or by the workflow -- is one the cited
evidence actually happened on. Then `coverage` measures where in the window the
citations fell, because long-context citation bias is real, is model-specific,
and is invisible without counting.

`work_only` is the one that does read URLs, and it answers a different
question: not "is this workflow honest about its evidence" but "is this
evidence a job anybody wanted mined". See its docstring.

Ported from `new_agent_arch/src/rig/checks.py`. Pure -- it reads `Window`,
`Workflow` and `Gesture` and nothing else, and is told what this deployment is
rather than reading settings -- so it lives in the domain beside them rather
than in the application layer with the mining pass that calls it.
"""

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture
from sro.domain.observation.identity import K_MIN_SHARED_STEPS
from sro.domain.observation.window import Window
from sro.domain.skill.workflow import Workflow, cited_ids, ordered_cites

K_MIN_COVERAGE = 0.5
K_MAX_SKEW = 0.4

_DEFAULT_PORTS = {"http": "80", "https": "443"}
"""`config._origins_of` keeps the same map for the same reason and cannot be
imported here: the domain reads settings through arguments or not at all."""


@dataclass(frozen=True, slots=True)
class Rejection:
    workflow_title: str
    reason: str
    detail: str


@dataclass(frozen=True, slots=True)
class Coverage:
    coverage: float
    skew: float
    gini: float


def validate(workflow: Workflow, evidence: dict[str, str]) -> Rejection | None:
    """None when the workflow may be kept, a Rejection when it may not.

    `evidence` maps a gesture id in the window to the system it happened on --
    `Gesture.system`, which is scheme and host. A missing or empty value means
    the system could not be established for that gesture.

    A mapping rather than a set of ids because the system checks below are the
    reason this module exists. Taking `step.system` as the evidence for
    `step.system` compared the model against itself: it caught an answer that
    contradicted its own step list and could not catch one that was internally
    tidy and wholly invented -- which, in an architecture built to find jobs
    spanning two systems, is the one lie it must not accept.
    """
    # umbrella.workflow_from drops junk steps one at a time, so a workflow whose
    # steps were ALL junk arrives here with steps=[] and no citations at all --
    # nothing uncited for the loop below to catch. This is that rejection.
    if not workflow.steps:
        return Rejection(workflow.title, "no steps", "a workflow of nothing")

    for step in workflow.steps:
        if not step.cites:
            return Rejection(workflow.title, "uncited step", f"step {step.order}: {step.says}")
        unknown = set(step.cites) - set(evidence)
        if unknown:
            return Rejection(workflow.title, "unknown gesture", ", ".join(sorted(unknown)))
        # cites' sibling. workflow_from falls back to says="" for a step the
        # model left unworded, and a step that says nothing is not a step
        # however well it is cited -- it reaches an operator as a blank line.
        if not step.says.strip():
            return Rejection(workflow.title, "wordless step", f"step {step.order}")
        # A step naming no system is not checked for one: the umbrella
        # substitutes None for a junk value, so an absent system is a silence
        # rather than a claim.
        if step.system:
            # An unknown system confirms nothing -- the rule shared_values and
            # correlate._owner already apply. So a step whose every citation is
            # unattributed is refused rather than waved through, and it is
            # refused under its own reason: "you named a system none of your
            # evidence touched" and "your evidence has no known system" are
            # different faults and diagnose differently.
            touched = {evidence[cite] for cite in step.cites if evidence[cite]}
            if not touched:
                return Rejection(
                    workflow.title,
                    "unattributed evidence",
                    f"step {step.order} claims {step.system}; no cited gesture has a system",
                )
            if step.system not in touched:
                return Rejection(
                    workflow.title,
                    "step system not in evidence",
                    f"step {step.order}: {step.system}",
                )

    claimed = {s for s in workflow.systems if s}
    # Every cite is in `evidence` by now, so this is the whole of what the
    # workflow actually stood on. `systems` is its own model output rather than
    # a summary of the steps, so it can name a system no step ever did.
    #
    # No `if evidence[cite]` filter, unlike the step check above, which needs
    # one to tell "no known system" from "the wrong system". Here `claimed` is
    # already truthy-only, so an unknown system arriving as "" can never match
    # anything it is subtracted from. Filtering both sides is one guard
    # pretending to be two -- deleting it changed no test.
    evidenced = {evidence[cite] for cite in cited_ids(workflow)}
    invented = claimed - evidenced
    if invented:
        return Rejection(workflow.title, "system not in evidence", ", ".join(sorted(invented)))

    # Last, because it is the only rejection here that is not about honesty.
    # Everything above catches a workflow that misdescribes its own evidence,
    # and those diagnose better than "too short" does -- a one-step proposal
    # that also cites a gesture nobody recorded should be refused for the
    # citation. This one is about what the rest of the system can do with an
    # honest answer.
    #
    # Fewer steps than `identity.resolve` needs to ever recognise this job
    # again. The bound is imported from the rule that causes it rather than
    # chosen here: `resolve` requires K_MIN_SHARED_STEPS shared shape entries
    # before it will call two proposals the same job, so a workflow with fewer
    # steps can only ever come back "new". Every pass over the same evidence
    # mints another copy and nothing ever merges them.
    #
    # Mined off the real acme store: a clean six-pass re-mine produced a second
    # `Create a Customer Type` of one step -- "Save the customer type
    # configuration" -- beside the real six-step job it was a fragment of. One
    # step is also not a job an operator would want offered: there is nothing
    # to parameterise and nothing in it to save them.
    if len(workflow.steps) < K_MIN_SHARED_STEPS:
        return Rejection(
            workflow.title,
            "too few steps to recognise",
            f"{len(workflow.steps)} step(s); resolve needs {K_MIN_SHARED_STEPS} to match",
        )
    return None


def _gini(values: list[float]) -> float:
    """How unequally the citations are spread. Only ever called with a full
    decile list that sums to 1, so it needs no empty case."""
    ordered = sorted(values)
    n = len(ordered)
    total = sum(ordered)
    weighted = sum((index + 1) * value for index, value in enumerate(ordered))
    return (2 * weighted) / (n * total) - (n + 1) / n


def coverage(workflows: list[Workflow], window: Window) -> Coverage:
    """Which parts of the window were cited at all, and where they clustered."""
    cited: set[str] = set()
    for workflow in workflows:
        cited |= cited_ids(workflow)

    n = len(window.items)
    deciles = [0.0] * 10
    for index, item in enumerate(window.items):
        if item.gesture_id in cited:
            deciles[index * 10 // n] += 1

    # An empty window skips the loop and lands here, so this is also the
    # no-items case: one return for "no citation fell anywhere in it".
    total = sum(deciles)
    if total == 0:
        return Coverage(0.0, 0.0, 0.0)
    mass = [d / total for d in deciles]
    return Coverage(
        # Over min(10, n) rather than a flat ten: a window of four gestures has
        # four parts and can only ever land in four deciles, so dividing by ten
        # reported a FULLY cited short window at 0.4 -- under K_MIN_COVERAGE.
        coverage=sum(1 for d in deciles if d > 0) / min(10, n),
        skew=sum(mass[:3]) - sum(mass[-3:]),
        gini=_gini(mass),
    )


def _origin(url: str) -> str:
    """A url as the system it belongs to: host and port, default port dropped.

    `https://wms.acme.com:443` and `https://wms.acme.com` are one system, and
    a rule that cannot say so refuses half the pages on it. Port and not
    hostname alone, because an API on 8000 beside a console on 3000 is the
    ordinary shape of this deployment.
    """
    parsed = urlsplit(url)
    host = (parsed.hostname or "").rstrip(".")
    if not host:
        return ""
    if ":" in host:
        host = f"[{host}]"
    try:
        port = str(parsed.port) if parsed.port else ""
    except ValueError:
        return ""
    if port and port == _DEFAULT_PORTS.get(parsed.scheme.lower()):
        port = ""
    return f"{host}:{port}" if port else host


def _passed_through(gesture: Gesture) -> bool:
    """Whether this gesture ended on a different system from the one it
    happened on -- the browser moved the operator, the operator did not."""
    here = _origin(gesture.system or "")
    return any(mark.url and _origin(mark.url) not in ("", here) for mark in gesture.page_events)


_WROTE_METHODS = frozenset({"POST", "PUT", "PATCH"})


def _signed_in_here(gesture: Gesture) -> bool:
    """Whether this gesture put a credential into the page.

    The recorder marks the password itself rather than the page around it, so
    this is the one fact about signing in that needs no list of hostnames --
    and a list is exactly what `work_only` below declined to keep, on the
    grounds that every customer runs an SSO nobody here has heard of.
    """
    target = gesture.action.target
    return bool(gesture.action.secret or (target is not None and target.secret))


def _did_business(gesture: Gesture) -> bool:
    """Whether this gesture wrote something to the system it happened on.

    A sign-in posts credentials to its identity provider, so "wrote something"
    on its own would call an identity host a working one. Same-origin is what
    separates them: signing in sends you somewhere else, and doing the job
    writes back to the page you are on.
    """
    here = _origin(gesture.system or "")
    return any(
        call.status is not None
        and 200 <= call.status < 300
        and call.method.upper() in _WROTE_METHODS
        and _origin(call.url) == here
        for call in gesture.requests
    )


def undeliverable(workflow: Workflow, gestures: dict[str, Gesture]) -> list[str]:
    """The declared parameters no step of this job could ever be given.

    `planning.value_for` is the one place a run's value reaches a control, and
    it looks the value up by four names in order: the component's `item_id`,
    its `field_label`, the target's `name`, and whatever the step itself listed
    in `parameters`. A workflow parameter whose name is none of those, on any
    step, is a name nothing will ever ask for.

    That is not a harmless spare field. `StartWorkflowRun` refuses a press that
    leaves a declared parameter empty, so the operator is made to type a value
    -- and then `value_for` never finds the name, falls through, and performs
    the step with the value the RECORDING happened to contain. The job runs,
    reports success, and did something other than what was asked. A parameter
    that cannot be delivered is worse than no parameter, because no parameter
    at least tells the truth.

    Found by reading what the miner actually produced. Three clean mines of one
    real day declared six parameters between them, and **three of the six named
    controls that do not exist in the evidence** -- `Description` where the
    label reads `Customer Type Description`, `Equipment Type` for `Warehouse
    Equipment Type`, `LPN Limit` for `LPN Warehouse Equipment Type Limit`.
    Those three bound anyway, but only because the model had written the same
    invented string into `step.parameters` as well, which `value_for` checks
    last. Nothing anywhere required those two halves of one model answer to
    agree.
    """
    bindable: set[str] = set()
    for step in workflow.steps:
        bindable.update(step.parameters)
        for cite in step.cites:
            gesture = gestures.get(cite)
            target = gesture.action.target if gesture else None
            component = target.component if target else None
            for name in (
                component.item_id if component else None,
                component.field_label if component else None,
                target.name if target else None,
            ):
                if name:
                    bindable.add(name)
    return [
        str(declared["name"])
        for declared in workflow.parameters
        if declared.get("name") and str(declared["name"]) not in bindable
    ]


def _during(workflow: Workflow, gestures: dict[str, Gesture]) -> list[Gesture]:
    """Every gesture of this job's own streams inside its own time span.

    A superset of what it cites, and the difference is the point: a citation
    list is a model's summary of a job, not its boundary, and a rule about what
    the operator did has to read the doing rather than the summary.

    Bounded by the cited gestures at both ends and by their streams, so this
    never reaches into another tab or into the next job along. A job that cites
    nothing gets nothing, which is `validate`'s problem and not this one.
    """
    cited = [gestures[one] for one in ordered_cites(workflow) if one in gestures]
    if not cited:
        return []
    first, last = min(one.at for one in cited), max(one.at for one in cited)
    streams = {one.stream_id for one in cited}
    return [
        gesture
        for gesture in gestures.values()
        if gesture.stream_id in streams and first <= gesture.at <= last
    ]


def work_only(
    workflow: Workflow, gestures: dict[str, Gesture], *, ours: frozenset[str]
) -> Rejection | None:
    """Strike the systems that were never the work, and refuse a job with none
    left. None when it may be kept, as `validate` answers.

    ``ours`` is this deployment itself as ``Settings.our_own_origins`` names
    it, host and port, no path -- a workflow's system is a scheme and a host
    and has no path to route on.

    Three things are struck. The first two were mined off the real acme
    store; the third off `new`, by the first pass that ever ran over real
    readings:

    **This product's own console.** `Review Video Recordings for Teach Task`
    is the miner watching somebody use SRO while capture was on. `admit`
    already refuses the apparatus at the door, which stops the NEXT one and
    does nothing about the day already in the store -- and the operator has
    deliberately emptied the tenant's exclusions, so capture is meant to stay
    whole and the judgment belongs here, where a job is proposed rather than
    where a gesture is kept.

    **A hop the browser bounced the operator through.** `Search for Work
    Areas` opened on `blueyonderalphaus.b2clogin.com` and
    `keycloak-...byp.ai`, which is a sign-in redirect chain read as the
    beginning of a job. A system is transit when the job carried on somewhere
    else afterwards AND some gesture on it ended on another system. Both
    halves are needed and each saves a real job the other would have lost: the
    WMS host bounced elsewhere on 4 of its 495 gestures, and is never struck
    because the work ends there; `mail.google.com` is read first and left for
    the WMS in two stored jobs, and is never struck because Gmail bounces
    nobody anywhere.

    **A job that is only signing in.** `Sign In to WMS` is three steps on an
    identity host and nothing else. The transit rule cannot reach it, and the
    credential the recorder already marks is what names it without keeping a
    list of hostnames. Refused rather than struck, because the claim is about
    the job and not about one of its systems -- see the comment below.

    What it wrongly strikes, said plainly: a job whose last act on one system
    is a hand-off link into another it never returns from -- raise it in the
    ticketing system, follow the link into the WMS, finish there. Real work on
    the first system, and this reads it as a doorway. Naming identity-provider
    domains instead would have been narrower and would also have been a list
    somebody has to keep, wrong for every customer running an SSO nobody here
    has heard of.
    """
    cited = [gestures[one] for one in ordered_cites(workflow) if one in gestures]
    order = [gesture.system or "" for gesture in cited]
    # Last occurrence per system: what matters is whether the job carried on
    # after this system the LAST time it was on it, not the first.
    last = {system: index for index, system in enumerate(order)}
    bounced = {gesture.system or "" for gesture in cited if _passed_through(gesture)}
    transit = {
        system
        for system, index in last.items()
        if system and index < len(order) - 1 and system in bounced
    }

    # A job that is only signing in. The transit rule above cannot reach this
    # one: it strikes a system the job carried on FROM, and a job that is only
    # a sign-in never carries on anywhere -- its last gesture is on the
    # identity host, so `index < len(order) - 1` is false and the hop stands as
    # if it were the work.
    #
    # `Sign In to WMS` is what that let through, mined off the real `new` store
    # by the first pass that ever ran over real readings: three steps on
    # `b2clogin.com` and a keycloak host, no parameters, and it would have been
    # offered to an operator as a job worth automating.
    #
    # Asked of the whole job rather than of one system, because that is the
    # claim -- not "this host is a doorway" but "nothing here was work". All
    # three halves are needed and each saves a job the others would lose:
    #
    # - a credential alone condemns the WMS itself on the day somebody mines
    #   setting a password for a new user, which is real warehouse work;
    # - no writes alone condemns every read-only job, and looking things up is
    #   most of what an operator does;
    # - a redirect alone condemns an honest hand-off, which `work_only` already
    #   says plainly it does not want to strike.
    #
    # Together they say: a password was typed, the browser moved the operator,
    # and nothing was ever written back. That is signing in, and it needs no
    # list of identity hostnames -- which this function declined to keep, on
    # the grounds that every customer runs an SSO nobody here has heard of.
    #
    # Asked of what the operator DID during this job, not of what the model
    # chose to cite about it -- and that distinction is the whole of whether
    # this rule fires at all. Shipped against `cited`, it could not fire on the
    # evidence it was written from: a clean re-mine of that same day proposed
    # `Log in to Warehouse Management System`, and this let it straight
    # through. The password gesture was in the store the whole time
    # (`action.secret` true, on the keycloak host) and the model had not cited
    # it -- reasonably, because redaction strips a credential gesture of its
    # value AND its target name, leaving nothing worth pointing at. So the one
    # gesture that proves a job is a sign-in is the one gesture a model
    # summarising that job will leave out.
    #
    # `during` is the cited gestures' own time span on the streams they cite,
    # which is the job as the operator lived it. Measured on that day: the
    # sign-in job's span holds the credential, and the two real jobs' spans
    # hold none -- including a Warehouse Equipment Type job whose span is 52
    # gestures wide.
    during = _during(workflow, gestures)
    if (
        any(_signed_in_here(gesture) for gesture in during)
        and any(_passed_through(gesture) for gesture in during)
        and not any(_did_business(gesture) for gesture in during)
    ):
        return Rejection(
            workflow.title,
            "not a job",
            "a credential was typed, the browser moved on, and nothing was written",
        )

    kept = [
        system
        for system in workflow.systems
        if _origin(system) not in ours and system not in transit
    ]
    # `workflow.systems` empty to begin with is a model that named none, which
    # `validate` allows and this must not start refusing: nothing was struck.
    if workflow.systems and not kept:
        return Rejection(
            workflow.title,
            "not a job",
            "every system it names is this deployment or a hop through one",
        )
    workflow.systems = kept
    return None


K_SITTING_GAP_S = 1800.0
"""How long a pause has to be before the work after it is a different doing.

Measured over both real corpora's nine stored jobs, clustering each job's
cited gestures by the gap between them:

| gap    | jobs left in one piece | `Create an Activity Code`'s biggest piece, of 31 |
|--------|------------------------|--------------------------------------------------|
| 1 min  | 5 of 9                 | 11                                               |
| 5 min  | 5 of 9                 | 27                                               |
| 30 min | 6 of 9                 | 30                                               |

**The binding case is the cross-system job, and it is why this is thirty
minutes and not five.** Tenant `new`'s `Create a Warehouse Equipment Type` is
the thing this whole architecture exists to find: step 1 reads a request on
`mail.google.com`, steps 2 to 7 create the equipment type on the real Blue
Yonder host. Its step 2 happened at 15:56 and its step 3 at 16:18 -- a
**22-minute** gap, because the operator read the mail, opened the WMS, and got
on with something else before typing. At five minutes that job splits, the
kept piece cannot supply step 2, and `validate` refuses the whole thing for an
uncited step. A bound tight enough to tidy acme's repeated single-system jobs
destroys the two-system job, which is the opposite of the trade this rig
exists to make.

Thirty still separates every welded job in the store -- `Create a Work Area`'s
two doings are 26 hours apart, `Create an Activity Code`'s 22 hours, `Create a
Work Operation`'s 75 minutes -- and leaves both of `new`'s cross-system jobs
whole. It is also a pause a person can reason about: the operator went to
lunch. Measured through the real matcher after this landed: acme went from 4
of 7 jobs offered as themselves to 5 of 7, `Create a Work Area` going from
never offered to offered at gesture 2 with 6 of its 7 values in hand.

**This is not the recogniser's bound, and the two are not the same question.**
`new-chrome-extension/src/background/recognise.js` keeps `K_TAIL_TTL_S = 600`:
a gesture older than ten minutes falls out of the tail before the next one
arrives. That bound bites only on the first `K_OFFER_AFTER` gestures, which is
why `new`'s cross-system job is offered at gesture 2 and never notices its own
22-minute pause at step 3 -- and why `Create an Activity Code`, whose first two
cited gestures are **26 minutes** apart, is still never offered after this
narrowing. A job the miner may keep whole is not automatically a job the
recogniser can hold, and nothing yet tells the miner that.
"""


def _sittings(times: list[float]) -> list[tuple[float, float]]:
    """Consecutive runs of `times`, split wherever the pause is long enough."""
    spans: list[tuple[float, float]] = []
    for at in sorted(times):
        if spans and at - spans[-1][1] <= K_SITTING_GAP_S:
            spans[-1] = (spans[-1][0], at)
        else:
            spans.append((at, at))
    return spans


def one_occurrence(workflow: Workflow, gestures: dict[str, Gesture]) -> None:
    """Strike every citation but one doing's, in place.

    A model asked to read a day and told that an operator often repeats a job
    does not always answer with one job per doing. It answers with ONE job
    whose every step cites every doing's gesture: step 1 of acme's `Create a
    Work Area` cites a gesture from 08-26 10:39 and another from 08-27 13:16,
    and calls that one step.

    That is not a harmless surplus of evidence. Three things read these
    citations and all three are wrong about a workflow built this way:

    * **The shape.** `shape_key` is built from the cited gestures in order, so
      a job done three times is served as a shape three doings long with the
      doings interleaved. The extension's matcher asks whether the operator's
      last *k* gestures ARE this shape's first *k*, and no single doing ever
      is. Measured on acme's seven jobs: the three with more than one doing in
      them are exactly the three the replay never offers.
    * **`learn_parameters`.** It needs a SECOND proposal to diff against the
      stored one. A pass that folds every doing into a single proposal never
      produces one, so a job the operator did four times can still be stored
      with no parameters at all.
    * **`_by_control`.** It keeps the last value per control in time order, so
      the other doings' values are silently dropped rather than becoming the
      `seen_values` range that makes a parameter useful.

    The doing kept is the one supplying citations to the most steps, and the
    latest of those if two tie -- latest because a re-mine should drift towards
    what the operator does now, not towards the first thing they ever did.

    A step left citing nothing is left that way rather than dropped here:
    `validate` refuses an uncited step, and a job whose steps do not all belong
    to one doing should be refused under that name rather than quietly
    reshaped into a shorter job nobody demonstrated.

    Nothing recovers the struck doings. They stay in the window and the pool,
    so the next pass reads them again -- which is the path that already exists
    for a second doing, and the path `learn_parameters` was written for.
    """
    times = [gestures[cited].at for cited in cited_ids(workflow) if cited in gestures]
    if not times:
        return
    spans = _sittings(times)
    if len(spans) < 2:
        return

    def reach(span: tuple[float, float]) -> tuple[int, float]:
        lo, hi = span
        steps = sum(
            1
            for step in workflow.steps
            if any(cited in gestures and lo <= gestures[cited].at <= hi for cited in step.cites)
        )
        return steps, hi

    lo, hi = max(spans, key=reach)
    for step in workflow.steps:
        step.cites = [
            cited for cited in step.cites if cited in gestures and lo <= gestures[cited].at <= hi
        ]
