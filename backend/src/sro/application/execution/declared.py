"""What a job's own fields are declared to hold, before any run finds out.

`workflow_learned.holds` is what a run MEASURED: it typed, the browser silently
kept a prefix, and the run wrote the number down so the next run of that job
would not have to spend a person's press rediscovering it. That works, and it
works one field at a time, one job at a time, and only after somebody has
already been sent a record that does not say what they asked for.

Somebody wrote the numbers down years ago. `index/field-dictionary.json` holds
404 payload keys with their screen labels and their `maxLength`, and
`index/form-models-all.json` holds 88 real create forms captured from the
application itself. Both are already ingested -- `infrastructure/knowledge/
catalogue.py` has read them into `field` and `form` claims since long before
the rig could type -- and nothing asked them what a JOB's parameters hold.

So this is a join and not a new source: the job names its parameters the way
the screen names them, the claims are filed under the key the body posts, and
the labels are the bridge. See `field_notes.limits_named` for the rule, which
is the interesting half: the lowest ceiling binds, and a label two keys answer
to decides nothing.

**Declared, and a declaration is not a measurement.** The dictionary says
`customerType` holds 60 and the real form says 4. So this is a ceiling handed
to `limits_for` beside what runs have learnt, never instead of it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.field_notes import limits_named
from sro.domain.knowledge.entry import EntryKind
from sro.domain.shared.hosts import screen_of
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Workflow

K_EVERY_FIELD = 800
"""How many field claims one lookup asks for.

Every one, rather than a search. `search` matches terms against a claim's title
and key, and what this needs to match is a LABEL inside the body -- so a lookup
for `Customer Type Description` scores on the title it happens to appear in and
misses the four keys it does not. Measured on QA 2026-09-16: 404 field claims.
Eight hundred is room for a base twice that size before a job stops seeing
fields it has.
"""

K_EVERY_FORM = 400
"""How many create forms one lookup asks for. `workflow_runs.K_EVERY_FORM` says
why every one rather than a search; 88 on this deployment."""


async def declared_limits(
    uow: UnitOfWork, tenant_id: TenantId, names: Sequence[str], screen: str = ""
) -> dict[str, int]:
    """What this job's parameters are documented to hold, by parameter name.

    The screen's own form first and the dictionary second, which is the order
    `limits_named` reads them in and the order the evidence deserves: a form
    model was captured from the form an operator actually uses, and the
    dictionary is what the vendor's manual says about a key across every screen
    that posts it.

    Empty for a job whose names nothing documents, which is the honest answer
    and the one that changes nothing -- a limit nobody declared is a limit the
    first run still finds out the hard way, exactly as it did before.
    """
    if not names:
        return {}
    async with uow as opened:
        fields = await opened.knowledge.search(
            tenant_id, kinds=(EntryKind.FIELD,), limit=K_EVERY_FIELD
        )
        forms = (
            await opened.knowledge.search(tenant_id, kinds=(EntryKind.FORM,), limit=K_EVERY_FORM)
            if screen.strip()
            else ()
        )
    return limits_named(
        names,
        _slots(forms, screen),
        {one.key: one.body for one in fields if isinstance(one.body, Mapping)},
    )


def _slots(forms: Sequence[object], screen: str) -> dict[str, dict[str, object]]:
    """The fields of whichever captured form this job's screen is.

    Joined on the route the form claim is keyed by, the same containment
    `workflow_runs._forms` uses -- and for its reason: a body key does not name
    a form, because `customerType` is posted by two of them on this deployment,
    so a lookup by key alone would lend one screen's numbers to another
    screen's write.
    """
    slots: dict[str, dict[str, object]] = {}
    for entry in forms:
        route = str(getattr(entry, "key", "") or "").rstrip("/")
        body = getattr(entry, "body", None)
        if not route or route not in screen or not isinstance(body, Mapping):
            continue
        fields = body.get("fields")
        for one in fields if isinstance(fields, list) else ():
            if not isinstance(one, Mapping) or not isinstance(slot := one.get("field"), str):
                continue
            said: dict[str, object] = {"observed": True}
            if isinstance(one.get("label"), str):
                said["labels"] = [one["label"]]
            if isinstance(cap := one.get("maxLength"), int) and not isinstance(cap, bool):
                said["max_length"] = cap
            slots.setdefault(slot, {}).update(said)
    return slots


def names_of(workflow: Workflow) -> list[str]:
    """What this job calls its fields, in the order it declares them.

    The JOB's parameters and not the steps', which are a different list for a
    good reason: a step's `parameters` say which step fills which name, and
    only a step that some demonstration actually varied has any. A job knows
    what it is about before it knows which step types it -- and this question
    is asked of a job that has not started.
    """
    return [
        name
        for parameter in workflow.parameters
        if isinstance(name := parameter.get("name"), str) and name.strip()
    ]


async def screen_for(uow: UnitOfWork, tenant_id: TenantId, workflow: Workflow) -> str:
    """The screen this job's fields are on, as its own demonstrations agree.

    A form claim is keyed by the route it was captured on, so a job with no
    screen gets the dictionary alone -- which is the weaker half, and the half
    that says `customerType` holds 60 when the form an operator uses says 4.
    Worth one read of the cited gestures to avoid.

    Only the steps that fill a parameter, which is narrower than it first
    looks and had to be. Measured on QA 2026-09-18 against the real `Create a
    Customer Type`: its six steps open a MAIL, navigate to the WMS, press Add,
    type twice and Save -- so the citations of all six are two systems, and
    `screen_of` anchors on the first url it is given and answers with the Gmail
    inbox. The form half then matched nothing, `Customer Type` came back as the
    manual's 60 rather than the real form's 4, and a card would have accepted
    `NEWSROTEST`, sent it, kept `NEWS` and been answered 201.

    Narrower is also more true. A limit is a fact about the box a value is
    typed into, so the screen worth asking about is the one the typing happens
    on -- not the one the job opens on, and not a collapse across both.

    Empty where no step declares a parameter, and the dictionary answers alone.
    That is the honest reading rather than a fallback to every step: a job with
    no typing step has no form to be measured against, and widening the net to
    find one is how the Gmail url got in here.
    """
    cites = tuple(sorted({one for step in workflow.steps if step.parameters for one in step.cites}))
    if not cites:
        return ""
    async with uow as opened:
        gestures = await opened.gestures.gestures_for(tenant_id, ids=cites)
    return screen_of([one.page_url or one.url for one in gestures]) or ""


__all__ = ["declared_limits", "names_of", "screen_for"]
