"""Typing a password a run was never allowed to record.

The operator asked the obvious question: it fills my username and presses Sign
In, so why can it not do the password. Because the recorder strikes a secret
field out at the boundary -- `redaction`, `trim.is_secret`, and `value_for`'s
own second belt -- and a recorded password is a password in a database, in a
mining prompt, and in whatever a model does with one afterwards.

So the value does not come from the recording. It comes from the vault, at the
moment the step is sent, by a key built from what the recording DOES hold: the
system, and the name of the field. Three properties follow, and they are the
whole design:

**The evidence plane never changes.** Redaction stays exactly as it was. What
a gesture stores about a password field is that there was one -- `secret:
true`, value `None` -- and that is all this needs to know which key to ask for.

**Nothing reads it back.** The vault has `get`, the route that stores one has
no sibling that returns it, and what the run RECORDS of a step is the payload
with the value struck out (`without_secrets`). A run's own history is read by
people, by the panel and by a model asked to rescue a failed step, and a
password in it would reach all three.

**An absent secret is a refusal with a sentence.** Not a blank field typed into
a login form, which submits, fails, and looks to everybody like the job being
broken. The step says which key it wanted, and the key is readable: the
operator can see they never stored one.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of

SECRET_MARK = "«from the vault»"  # noqa: S105 - a marker written INSTEAD of a password
"""What a recorded step says where the value was. Visible on purpose: a step
whose payload showed nothing at all would read as a step that types nothing,
and this one types the most important thing on the page."""


def field_of(gesture: Gesture) -> str:
    """The name of the control, as a person would recognise it.

    The field label first, then the control's own name, then its id: the label
    is what the operator read on screen when they typed into it, and the key
    they will later store a secret under has to be one they can recognise.

    Lowercased and stripped to letters, digits and dashes, because this becomes
    half of a vault key and a key with a space in it is a key somebody types
    wrong once and then cannot find.
    """
    target = gesture.action.target
    component = target.component if target else None
    for name in (
        component.field_label if component else None,
        target.name if target else None,
        component.item_id if component else None,
    ):
        if name and name.strip():
            return _as_key(name)
    return "password"


def _as_key(name: str) -> str:
    """A field's name as half a vault key: lowercase, letters, digits, dashes.

    A key with a space in it is a key somebody types wrong once and then cannot
    find -- and the two sides of this, the run asking and the operator storing,
    have to spell it the same way or the value is invisible to the one thing
    that needs it.
    """
    return re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")


def secret_key_for(tenant_id: str, gesture: Gesture) -> str:
    """Where this control's value lives in the vault.

    `tenant/system/field`, which is `Connection.credential_key`'s shape rather
    than a second one: a deployment that already stored a password for a
    connection and one that stores it for a step should not have two vaults
    with two spellings between them.

    The system is the ORIGIN and not the page. An operator signs in once for a
    host, not once per url, and a key per url would be a password they have to
    store again the first time the login page carries a different query.
    """
    system = origin_of(gesture.url or "") or origin_of(gesture.system or "") or "unknown"
    return f"{tenant_id}/{system}/{field_of(gesture)}"


def secret_key_of(tenant_id: str, system: str, field: str) -> str:
    """The same key, from the parts a person types when they store one.

    `secret_key_for` builds it from a gesture, which is what a RUN has. This
    builds it from a system and a field, which is what an operator has when
    they are looking at a step that refused and named the key it wanted. One
    function each and one rule between them: both normalise the field the same
    way, or the key stored under is not the key asked for and the value is
    invisible to the only thing that needs it.
    """
    return f"{tenant_id}/{origin_of(system) or system.strip().lower()}/{_as_key(field)}"


def connector_key(tenant_id: str, server: str, principal_id: str) -> str:
    """Where ONE operator's grant for one connector lives.

    Per operator and not per tenant, because each reads their own mail: a key
    without the person in it would have one operator's mailbox answering for
    everybody in the tenant, which is the same bug one scope smaller.

    The principal is HASHED into the field rather than spelled, and that is the
    whole care of this function. `_as_key` collapses every run of punctuation
    to a single dash, so `devansh.j` and `devansh_j` and `devansh j` are one
    key -- and `PrincipalId` constrains nothing but blankness, so all three are
    ids somebody can be issued. A collision here is one operator reading
    another's mail, which is precisely what `secret_manager`'s own docstring
    warns about one segment to the left.

    Hex, so `_as_key` passes it through untouched and there is still exactly
    one function shaping vault keys. Unreadable on purpose, and answered by the
    connector printing the key beside the bearer it mints.
    """
    named = hashlib.sha256(principal_id.encode()).hexdigest()[:32]
    return secret_key_of(tenant_id, server, f"mcp-token-{named}")


def needs_a_secret(gesture: Gesture) -> bool:
    """Whether this step types something the recording was not allowed to keep.

    The same question `value_for` answers with `None`. Asked separately because
    the two answers differ now: `value_for` still refuses to take a credential
    from the RECORDING, and this says the value may come from the vault
    instead.
    """
    target = gesture.action.target
    return bool(target and target.secret)


def without_secrets(payload: Mapping[str, object]) -> dict[str, object]:
    """The payload as it is written down: everything but the value.

    A run's steps are read by the panel, by an operator reviewing what
    happened, and by a model asked to rescue the step after it failed. A
    password in `workflow_run_steps.sent` would reach all three, and the row
    outlives the run by as long as the tenant keeps its evidence.
    """
    # `None` is not a value to strike out. A click carries `value: None` --
    # the planner fills the field for every command shape -- and marking it
    # put "«from the vault»" on the Sign In click in a real run's record,
    # which says a password was typed by a step that typed nothing.
    if payload.get("value") is None:
        return dict(payload)
    return {**payload, "value": SECRET_MARK}
