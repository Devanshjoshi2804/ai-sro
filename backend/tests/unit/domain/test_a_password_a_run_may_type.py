"""Where a password comes from, and the three places it must never appear.

An operator watched their browser fill a username, press Sign In and leave the
password blank, and asked why. Because the recorder strikes a secret field out
at the boundary and always will -- a recorded password is a password in the
evidence plane, in a mining prompt, and in whatever a model does with one.

So the value is not recorded. It is stored once, deliberately, and fetched at
the moment the step types it. What is held here is the key rule -- both sides
have to spell it the same way or the value is invisible to the only thing that
needs it -- and the mark that goes into the run's own record instead.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from sro.domain.execution.secrets import (
    SECRET_MARK,
    field_of,
    needs_a_secret,
    secret_key_for,
    secret_key_of,
    without_secrets,
)
from sro.domain.observation.gesture import Action, Component, Gesture, Target

KEYCLOAK = "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
SIGN_IN = f"{KEYCLOAK}/auth/realms/bf56-001-eus2/protocol/openid-connect/auth?client_id=x"


def _typed(
    *,
    secret: bool = True,
    name: str | None = "password",
    label: str | None = None,
    url: str = SIGN_IN,
    system: str = KEYCLOAK,
) -> Gesture:
    target = Target(
        tag="input",
        name=name,
        secret=secret,
        component=Component(field_label=label) if label else None,
    )
    return Gesture(
        id="ges-1",
        tenant="new",
        stream_id="str-1",
        batch_id="bat-1",
        at=1_000.0,
        url=url,
        system=system,
        tab_id=7,
        frame_url=None,
        action=Action(kind="type", at=1_000.0, url=url, target=target, value=None),
    )


def test_a_secret_field_is_what_makes_a_step_ask_the_vault() -> None:
    assert needs_a_secret(_typed())
    assert not needs_a_secret(_typed(secret=False))


def test_a_gesture_marked_secret_on_its_action_alone_is_the_password_field_too() -> None:
    """The sign-in chain takes such a gesture for the password; typing the
    recorded, redacted value there instead would read as a refused password."""
    typed = _typed(secret=False)

    assert needs_a_secret(replace(typed, action=replace(typed.action, secret=True)))


def test_the_key_is_the_system_and_the_field_and_not_the_page() -> None:
    """An operator signs in once for a host. A key per url is a password they
    would have to store again the first time the sign-in page carried a
    different query -- and this page's url carries a fresh `client_id`, a
    `state` and a nonce on every visit."""
    key = secret_key_for("new", _typed())

    assert key == ("new/keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai/password")
    assert "client_id" not in key


def test_the_operator_and_the_run_spell_the_same_key() -> None:
    """The whole design rests on this. The run builds a key from a gesture; the
    person storing one builds it from a system and a field they read off the
    step that refused. Two functions, one rule -- or the value is invisible to
    the only thing that needs it."""
    from_a_gesture = secret_key_for("new", _typed())
    from_a_person = secret_key_of(
        "new", "keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai", "Password"
    )

    assert from_a_gesture == from_a_person


@pytest.mark.parametrize(
    ("system", "field"),
    [
        (f"{KEYCLOAK}/auth/realms/x", "password"),
        ("keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai", " PASSWORD "),
        (KEYCLOAK, "Password "),
    ],
    ids=["a url they pasted", "spacing and case", "a scheme"],
)
def test_a_person_storing_one_does_not_have_to_type_it_perfectly(system: str, field: str) -> None:
    assert secret_key_of("new", system, field) == secret_key_for("new", _typed())


def test_a_schemeless_system_does_not_leak_its_userinfo_into_the_key() -> None:
    key = secret_key_of("new", "bob:hunter2@wms.example", "password")

    assert key == "new/wms.example/password"
    assert "hunter2" not in key


# -- where the system half of the key comes from -------------------------------
#
# Three sources in order -- the gesture's url, the gesture's system, then
# `unknown` -- and the fixture above sets both of the first two to the SAME
# host, so nothing here discriminated between them: a sweep found the whole
# fallback chain surviving, including the literal `unknown`. This is the half
# of the key an operator does not type, and if the run derives it differently
# from `secret_key_of` the password is stored under one key and asked for under
# another, which is a step refusing at 3am over a value that is in the vault.


def test_the_page_the_operator_typed_on_names_the_key_before_the_stream_does() -> None:
    """A gesture carries both, and they can disagree: `system` is the stream's
    host and `url` is the frame the control was actually in. The password
    belongs to the form the operator typed into."""
    key = secret_key_for("new", _typed(url="https://login.example/auth", system="https://wms.test"))

    assert key == "new/login.example/password"


def test_a_gesture_with_no_page_falls_back_to_the_stream_it_came_from() -> None:
    """A gesture whose url never made it -- a frame that reported none -- still
    knows which system it was recorded against, and that is a better key than
    giving up."""
    key = secret_key_for("new", _typed(url="", system="https://wms.test"))

    assert key == "new/wms.test/password"


def test_a_gesture_that_names_no_system_at_all_keys_under_a_word_a_person_reads() -> None:
    """`unknown`, spelled exactly. The step that refuses shows the key it
    wanted so the operator can store one under it -- a key they cannot read is
    a key they cannot fill, and this is the only half they would have to copy
    rather than recognise."""
    assert secret_key_for("new", _typed(url="", system="")) == "new/unknown/password"


def test_the_field_is_named_the_way_the_operator_saw_it() -> None:
    # The label on screen first: it is what they read when they typed into it,
    # and the key they store under has to be one they recognise.
    assert field_of(_typed(label="Password or PIN", name="j_password")) == "password-or-pin"
    assert field_of(_typed(label=None, name="j_password")) == "j-password"


def test_a_control_with_no_name_at_all_is_still_askable_for() -> None:
    """A login form that names nothing is still a login form. `password` is the
    honest default, and an operator can see the key on the refused step."""
    assert field_of(_typed(label=None, name=None)) == "password"


def test_what_the_run_writes_down_is_the_mark_and_not_the_value() -> None:
    """The row this becomes is read by the panel, by an operator reviewing what
    happened, and by the model asked to rescue a failed step. It outlives the
    run by as long as the tenant keeps its evidence."""
    recorded = without_secrets({"action": "type", "value": "hunter2", "origin": KEYCLOAK})

    assert recorded["value"] == SECRET_MARK
    assert "hunter2" not in str(recorded)
    # Everything else survives: a step whose record showed nothing would read
    # as a step that typed nothing, and this one types the most important
    # thing on the page.
    assert recorded["action"] == "type" and recorded["origin"] == KEYCLOAK


def test_a_payload_with_no_value_is_left_exactly_as_it_is() -> None:
    assert without_secrets({"action": "click"}) == {"action": "click"}


def test_a_command_that_types_nothing_is_not_said_to_have_typed_a_password() -> None:
    """A click carries `value: None` -- the planner fills the field for every
    command shape -- and marking it put "«from the vault»" on the Sign In click
    of a real run, which reads as a password typed by a step that typed
    nothing."""
    assert without_secrets({"action": "click", "value": None})["value"] is None


# -- the fallback chain in the key, which nothing walked ----------------------
#
# `secret_key_for` reads `origin_of(url) or origin_of(system) or "unknown"`.
# Every test above hands it a gesture with a url, so only the first branch was
# ever taken and the other two could say anything at all: a mutation sweep
# found twelve survivors on that one line and on `_as_key`'s trailing strip.
#
# The branches are not decoration. The key is where a password LIVES, and the
# operator storing one and the run asking for it have to spell it the same way
# -- so a fallback that quietly produced a different system, or an empty
# segment, would hide the value from the only thing that needs it, and hide it
# silently, as a login that submits blank.


def test_a_gesture_with_no_url_falls_back_to_the_system_it_happened_on() -> None:
    """Some gestures carry no url of their own -- a keypress inside a frame,
    an event the recorder saw without a navigation. The system is still known,
    and it is the half of the key that has to stay stable."""
    without_url = _typed(url="")

    assert secret_key_for("new", without_url) == f"new/{_origin(KEYCLOAK)}/password"


def test_a_gesture_with_neither_is_keyed_somewhere_a_person_can_still_find() -> None:
    """Never blank. A key with an empty segment reads as `new//password`,
    which an operator cannot type and cannot recognise; `unknown` is at least
    a word, and a step that refused will print the key it wanted."""
    nowhere = _typed(url="")
    nowhere.system = None

    assert secret_key_for("new", nowhere) == "new/unknown/password"


def test_the_field_name_keeps_no_dash_at_either_end() -> None:
    """`_as_key` replaces every run of other characters with a dash, so a
    label that starts or ends with punctuation would key as `-password` or
    `password-`. The operator types what they read on screen; they do not type
    the dash the substitution left behind."""
    assert field_of(_typed(name="Password:")) == "password"
    assert field_of(_typed(name="* Password *")) == "password"
    assert field_of(_typed(name="Your password!")) == "your-password"


def _origin(url: str) -> str:
    from sro.domain.shared.hosts import origin_of

    return origin_of(url) or ""
