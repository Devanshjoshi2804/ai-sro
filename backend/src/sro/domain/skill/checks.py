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


def work_only(
    workflow: Workflow, gestures: dict[str, Gesture], *, ours: frozenset[str]
) -> Rejection | None:
    """Strike the systems that were never the work, and refuse a job with none
    left. None when it may be kept, as `validate` answers.

    ``ours`` is this deployment itself as ``Settings.our_own_origins`` names
    it, host and port, no path -- a workflow's system is a scheme and a host
    and has no path to route on.

    Two things are struck, and both were mined off the real acme store:

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
