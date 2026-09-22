"""The step a model will never write: typing the password.

An operator asked, more than once, why their browser fills their username,
presses Sign In, and leaves the password blank. The mined job really does have
two steps and no third one, and the reason is upstream of the model:

    redaction strips a credential gesture of its value AND its target name,
    leaving nothing worth pointing at

-- `checks.py` says exactly that, and draws the right conclusion for what it
was doing: the one gesture that proves a job is a sign-in is the one gesture a
model summarising that job will leave out. It is invisible for the same reason
it is safe.

So the step is not asked for. It is ADDED, here, from the evidence the model
was summarising, under rules narrow enough that a job which is not a sign-in
cannot grow one by accident:

**Only a gesture the recorder marked secret.** Not "a field called password" --
the recorder's own mark, the same one `is_secret` reads, set at the boundary
where a real browser saw a real input of type password.

**Only inside the doing the workflow kept.** `one_occurrence` has already
struck every citation but one doing's by the time this runs, so the span is
that doing: a credential typed in another hour, or in another job, is not this
job's password.

**Only where no step already covers it.** A model that did cite the credential
gesture -- rare, but it happens when the field carries a label the redaction
leaves alone -- keeps its own step and gets no second one.

**Never a value.** The step cites the gesture and nothing else. What gets typed
comes from the vault at run time (`domain/execution/secrets`), by a key built
from the system and the field. The evidence still holds no password, and this
module never sees one.
"""

from __future__ import annotations

from sro.domain.execution.evidence import PUTS_A_VALUE, primary_gesture
from sro.domain.execution.secrets import field_of
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step, Workflow


def with_passwords(workflow: Workflow, gestures: dict[str, Gesture]) -> int:
    """Give this job the credential steps it does and the model did not say.

    In place, returning how many steps it CHANGED -- added, or removed as a
    second attempt at the same field. A job with no credential in its span is
    untouched and answers 0, which is most jobs, because most work is not
    signing in.
    """
    cited = {
        gesture_id for step in workflow.steps for gesture_id in step.cites if gesture_id in gestures
    }
    if not cited:
        return 0

    within = [gestures[gesture_id] for gesture_id in cited]
    first, last = min(one.at for one in within), max(one.at for one in within)
    systems = {origin_of(one.url or "") for one in within}

    # ONE step per field, and the first typing of it.
    #
    # The first real login this ran against had four. The operator had typed
    # their password four times inside that doing -- a mistyped attempt, a page
    # that came back, a second go -- and every one of them became a step, two
    # of them AFTER the Sign In click, which is not a login: it is a job that
    # signs in, fails, and types a password into whatever came next.
    #
    # A person typing a password twice is one step done twice, so the earliest
    # is the one that belongs before the submit, and the rest are attempts.
    # Keyed by system and field rather than by gesture, because that is what
    # makes two typings the same step -- and it is the same key the vault is
    # read by, so a job cannot end up with two steps asking for one secret.
    once: dict[tuple[str, str], Gesture] = {}
    for gesture in sorted(gestures.values(), key=lambda one: one.at):
        # A credential step TYPES one. A click on a password box is a person
        # putting the cursor in it, and on this deployment it happened first --
        # so the earliest-wins rule below chose the click, built the whole
        # reading around it, and the job ended up with a step that pressed
        # Sign In having typed nothing (`wfl_7fa53354`, 2026-09-22).
        if not is_secret(gesture) or gesture.action.kind not in PUTS_A_VALUE:
            continue
        # The doing this workflow kept, and the systems it was done on. A
        # credential typed an hour later, or on a host this job never touched,
        # belongs to somebody else's job.
        if not first <= gesture.at <= last:
            continue
        where = origin_of(gesture.url or "")
        if where not in systems:
            continue
        once.setdefault((where, field_of(gesture)), gesture)

    # Steps that cite a typing this rule did not choose: a second attempt,
    # written by an earlier version of this rule or by a model that cited one.
    # Dropped rather than left, so a job heals rather than accumulating the
    # shape of whichever day it was mined on.
    kept = {gesture.id for gesture in once.values()}
    spare = [
        step
        for step in workflow.steps
        if step.cites
        and all(one in gestures and is_secret(gestures[one]) for one in step.cites)
        and not any(one in kept for one in step.cites)
    ]
    for step in spare:
        workflow.steps.remove(step)

    # A credential is covered when a step is AIMED at it, not when anything
    # happens to mention it.
    #
    # A step cites what the operator did while performing it, and on a login
    # that is both boxes: `Enter username or email` on this deployment cited
    # the username's type and the password's. The credential was therefore
    # "cited", this rule skipped it, and the step the model had named `Type
    # the password.` was left citing a CLICK on the box -- so every run of
    # that job planned a click at a password field, typed nothing, and pressed
    # Sign In. Measured 2026-09-22, `wfl_7fa53354`: nine runs, no password
    # ever typed by the two that reached it.
    #
    # `primary_gesture` is the same reading the planner makes of a step, which
    # is what makes this the right question: if the planner would not aim at
    # the credential, no step types it, whoever cites it.
    aimed = set()
    for step in workflow.steps:
        at = primary_gesture(step, gestures)
        if at is not None and is_secret(at):
            aimed.add(at.id)
    added = 0
    for gesture in sorted(once.values(), key=lambda one: one.at):
        if gesture.id in aimed:
            continue
        workflow.steps.append(
            Step(
                order=0,  # renumbered below, once, in time order
                says=f"Type the {field_of(gesture).replace('-', ' ')}.",
                # The gesture's SYSTEM and not its url. `validate` checks a
                # step's system against the systems its cited evidence was
                # attributed to, so a step naming the page it happened on is a
                # step refused for claiming a system none of its evidence
                # touched -- which is the whole job refused, over the one step
                # the model could not see.
                system=gesture.system,
                cites=[gesture.id],
                parameters=[],
            )
        )
        added += 1

    # Renumbered when anything moved, which includes a spare step removed and
    # nothing added: a job left with a hole in its numbering is a job whose
    # steps no longer say what order they run in.
    if added or spare:
        _in_the_order_it_happened(workflow, gestures)
    return added + len(spare)


def _in_the_order_it_happened(workflow: Workflow, gestures: dict[str, Gesture]) -> None:
    """Renumber every step by when its evidence happened.

    A password step appended to the end would be typed after Sign In was
    pressed, which is not a login, it is a page that has already refused. The
    order the operator did it in is the only order that runs, and the evidence
    carries it -- so this sorts by the earliest gesture each step cites rather
    than trusting the model's numbering, which was correct for the steps it
    knew about and knows nothing about this one.
    """

    def when(step: Step) -> float:
        times = [gestures[one].at for one in step.cites if one in gestures]
        # A step citing nothing this pass can see keeps its place rather than
        # being thrown to the front: `validate` refuses an uncited step, so
        # this is a step whose evidence is simply not in this window.
        return min(times) if times else float(step.order)

    for position, step in enumerate(sorted(workflow.steps, key=when)):
        step.order = position
