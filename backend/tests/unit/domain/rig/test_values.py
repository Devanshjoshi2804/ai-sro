from dataclasses import replace

from sro.domain.observation.gesture import Gesture, Intent, PageMark, ValueSeen
from sro.domain.observation.values import (
    K_MIN_LONE_WORD,
    K_MIN_VALUE_LEN,
    K_UBIQUITY,
    frequencies_over,
    shared_values,
    trivial,
    typed_values,
    worked_in_both,
)
from tests.unit.domain.rig.conftest import gestures as _gestures


def test_a_typed_value_is_found() -> None:
    typed = next(g for g in _gestures() if g.action.kind == "type" and g.action.value)

    assert typed.action.value in typed_values(typed, None)


def test_a_value_the_reading_saw_is_found_too() -> None:
    gesture = _gestures()[0]
    intent = Intent(
        gesture_id=gesture.id,
        tenant="acme",
        values_seen=[ValueSeen(field="supplier", value="TestYonder2")],
    )

    assert "TestYonder2" in typed_values(gesture, intent)


def test_a_credential_value_is_never_a_link() -> None:
    """It is not in the gesture to begin with, and must not arrive by any
    other route either.

    The first assertion alone cannot fail: the wire parser nulls a credential
    at parse time, so it holds with the is_secret guard deleted entirely. The
    route that can fail is the model's -- it is shown the field the value went
    into, and values_seen comes back unvalidated, so a password echoed there
    became a cross-system link."""
    secret = next(g for g in _gestures() if g.action.secret)

    assert typed_values(secret, None) == set()

    echoed = Intent(
        gesture_id=secret.id,
        tenant="acme",
        values_seen=[ValueSeen(field="password", value="hunter2")],
    )

    assert typed_values(secret, echoed) == set()


def test_something_too_short_links_nothing() -> None:
    """Two floors, because a lone word and a phrase collide at different
    lengths. K_MIN_VALUE_LEN is the floor for anything with a separator in it;
    a bare word has to clear K_MIN_LONE_WORD, since `test` in five
    applications is a coincidence and `Test Drive LLC` in three is a carrier."""
    assert trivial("SG", 0.0) is True
    assert trivial("x" * K_MIN_VALUE_LEN, 0.0) is True, "a lone word this short collides"
    assert trivial("x" * K_MIN_LONE_WORD, 0.0) is False
    assert trivial("x" * K_MIN_VALUE_LEN + " y", 0.0) is False, "two words clear the lower floor"


def test_a_value_on_every_call_is_furniture() -> None:
    """A facility code every call carries links nothing; a supplier name typed
    once in two systems links a great deal."""
    assert trivial("DC1-WAREHOUSE", 0.9) is True
    assert trivial("DC1-WAREHOUSE", 0.01) is False


def test_a_value_seen_in_one_system_only_is_not_a_crossing() -> None:
    gestures = _gestures()
    intents = {
        g.id: Intent(
            gesture_id=g.id, tenant="acme", values_seen=[ValueSeen(field="f", value="ACME-4471")]
        )
        for g in gestures
    }

    assert shared_values(gestures, intents, {}) == {}


def test_a_value_in_two_systems_is_a_crossing() -> None:
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    intents = {
        g.id: Intent(
            gesture_id=g.id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="TestYonder2")],
        )
        for g in gestures
    }

    crossings = shared_values(gestures, intents, {})

    assert "TestYonder2" in crossings
    assert set(crossings["TestYonder2"]) == {gestures[0].id, gestures[1].id}


def test_furniture_with_whitespace_around_it_is_still_furniture() -> None:
    """trivial() and frequencies_over() strip; shared_values did not, so the
    frequency lookup missed and furniture at 1.0 was published as a link."""
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    intents = {
        g.id: Intent(
            gesture_id=g.id,
            tenant="acme",
            values_seen=[ValueSeen(field="site", value=" DC1-WAREHOUSE ")],
        )
        for g in gestures
    }

    assert shared_values(gestures, intents, {"DC1-WAREHOUSE": 1.0}) == {}


def test_one_value_written_four_ways_is_one_crossing() -> None:
    """Otherwise a real crossing splits into several and none of them cross."""
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    intents = {
        gestures[0].id: Intent(
            gesture_id=gestures[0].id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="Supplier-X")],
        ),
        gestures[1].id: Intent(
            gesture_id=gestures[1].id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="Supplier-X\n")],
        ),
    }

    crossings = shared_values(gestures, intents, {})

    assert set(crossings) == {"Supplier-X"}
    assert set(crossings["Supplier-X"]) == {gestures[0].id, gestures[1].id}


def test_a_gesture_with_no_known_system_does_not_make_a_crossing() -> None:
    """An unknown system is not a second system. `system or ""` made it one, so
    one unattributable gesture beside one real system reported a crossing."""
    gestures = _gestures()[:2]
    gestures[0].system = None
    gestures[1].system = "https://sap.example"
    intents = {
        g.id: Intent(
            gesture_id=g.id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="SUPPLIER-X")],
        )
        for g in gestures
    }

    assert shared_values(gestures, intents, {}) == {}


def _ten_gestures() -> list[Gesture]:
    """Ten copies of one real gesture, each with its own id and no typed value.

    The value is cleared so that each test below controls exactly one source --
    the reading, or the typing -- rather than both at once.
    """
    template = _gestures()[0]
    made = []
    for n in range(10):
        gesture = replace(template, id=f"ges_{n}")
        gesture.action = replace(template.action, value=None)
        made.append(gesture)
    return made


def test_a_value_named_twice_in_one_reading_is_one_gesture() -> None:
    """K_UBIQUITY is a coverage fraction. Counting mentions instead of gestures
    marked a value seen on a single gesture out of ten as furniture at 0.3 and
    dropped it from every crossing."""
    gestures = _ten_gestures()
    intents = {
        gesture.id: Intent(
            gesture_id=gesture.id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="SUPPLIER-X")] * 2
            if n == 0
            else [ValueSeen(field="site", value="DC1-WAREHOUSE")],
        )
        for n, gesture in enumerate(gestures)
    }

    frequencies = frequencies_over(gestures, intents)

    assert frequencies["SUPPLIER-X"] == 0.1
    assert frequencies["SUPPLIER-X"] <= K_UBIQUITY


def test_a_value_only_ever_typed_can_still_be_furniture() -> None:
    """The counted source used to be values_seen alone -- model output. A value
    the operator typed on every gesture and that no reading ever echoed looked
    up at 0.0, cleared trivial()'s ubiquity bar every time, and could never be
    classified as furniture however much of the day it covered."""
    gestures = _ten_gestures()
    for gesture in gestures:
        gesture.action = replace(gesture.action, value="DC1-WAREHOUSE")
    # Read, but the readings echo something else entirely: the only place
    # "DC1-WAREHOUSE" appears is the typing.
    intents = {
        gesture.id: Intent(
            gesture_id=gesture.id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value=f"SUPPLIER-{n}")],
        )
        for n, gesture in enumerate(gestures)
    }

    frequencies = frequencies_over(gestures, intents)

    assert frequencies["DC1-WAREHOUSE"] == 1.0
    assert trivial("DC1-WAREHOUSE", frequencies["DC1-WAREHOUSE"])
    # And the value it is being told apart from is not furniture.
    assert frequencies["SUPPLIER-0"] == 0.1
    assert not trivial("SUPPLIER-0", frequencies["SUPPLIER-0"])


def test_one_gesture_saying_a_value_twice_is_cited_once() -> None:
    """typed_values is a set, so the same value typed and reported collapses --
    but only if it is stripped before the set is built. Stripping in the caller
    deduplicated nothing, and the gesture was cited twice for one doing."""
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    typed = gestures[0].action.value
    assert typed
    intents = {
        gestures[0].id: Intent(
            gesture_id=gestures[0].id,
            tenant="acme",
            values_seen=[ValueSeen(field="code", value=f" {typed} ")],
        ),
        gestures[1].id: Intent(
            gesture_id=gestures[1].id,
            tenant="acme",
            values_seen=[ValueSeen(field="code", value=typed)],
        ),
    }

    crossings = shared_values(gestures, intents, {})

    assert crossings[typed] == [gestures[0].id, gestures[1].id]


def test_a_non_str_value_from_the_store_does_not_take_the_crossing_down() -> None:
    """api._row_to_intent builds ValueSeen(**seen) from unvalidated stored JSON
    and ValueSeen is a plain dataclass, so a bare .strip() here raises
    AttributeError on an int. Unreachable today; the defence keeps it so."""
    gesture = next(g for g in _gestures() if not g.action.secret)
    intent = Intent(
        gesture_id=gesture.id,
        tenant="acme",
        # `ValueSeen.value` is typed `str`; the store hands back unvalidated
        # JSON where it is not, which is the case `str(seen.value)` defends.
        values_seen=[ValueSeen(field="qty", value=42)],
    )

    assert "42" in typed_values(gesture, intent)


def test_a_lone_short_word_is_not_a_crossing() -> None:
    """`test` is exactly K_MIN_VALUE_LEN and, on an all-tabs day, appeared in
    five hosts at ubiquity 0.025 -- under the furniture threshold, over the
    length floor, published as a cross-system link. A junk crossing is worse
    than noise: strength uses crossings to pull evidence INTO the window."""
    assert trivial("test", 0.0)
    assert trivial("open", 0.0)
    assert trivial("save", 0.0)


def test_a_real_identifier_is_kept_however_it_is_spelled() -> None:
    """Blocklisting the word was the obvious fix and the corpus refuses it:
    `Test Drive LLC` is a real carrier in this tenant's capture and a genuine
    crossing, and it contains `Test` as a whole word. Every value below is from
    the real store."""
    for value in (
        "Test Drive LLC",
        "AITEST9",
        "Enveyo",
        "005-BEST METHOD",
        "ConnectShip (TanData)",
        "SHONEK TRANSPORTATION INC",
        "Process Work Status Change For Storage Equipment",
    ):
        assert not trivial(value, 0.0), value


MAIL = "https://mail.google.com"
WMS = "https://wms.example"
IDP = "https://login.example"


def _at(system: str, at: float, *, moved_to: str | None = None) -> Gesture:
    """One gesture on one system at one moment, and where the browser went
    next if it took the operator somewhere.

    Nothing is typed. That is the point of every test below: the value rule has
    nothing to work with, which is exactly the shape of reading a mail.
    """
    one = replace(_gestures()[0], id=f"ges_{system[8:12]}_{at:.0f}", at=at, system=system)
    one.action = replace(one.action, value=None)
    one.url = f"{system}/page"
    moved = [PageMark(at=at, page_kind="navigated", url=f"{moved_to}/landing")]
    one.page_events = moved if moved_to else []
    return one


def test_a_tab_somebody_went_back_to_is_work_in_two_systems() -> None:
    """The shape the value rule cannot see: read the mail, create the thing it
    asks for, go back to the mail. Nothing is typed into the mail, so no value
    crosses -- and on the real acme store this is an operator reading a mail
    whose subject is "create a customer type :" and typing the value into the
    warehouse six seconds later."""
    sitting = [
        _at(MAIL, 100),
        _at(WMS, 106),
        _at(MAIL, 120),
        _at(WMS, 130),
    ]

    linked = worked_in_both(sitting, gap=600)

    assert linked == {g.id for g in sitting}
    assert shared_values(sitting, {}, {}) == {}, "nothing typed crossed: the value rule sees none"


def test_a_system_visited_once_is_not_a_second_tab() -> None:
    # Going somewhere and staying is one system's work with a preamble. Coming
    # BACK is what says two tabs were being used for one thing.
    sitting = [_at(MAIL, 100), _at(WMS, 110), _at(WMS, 120), _at(WMS, 130)]

    assert worked_in_both(sitting, gap=600) == set()


def test_a_doorway_the_browser_bounced_through_links_nothing() -> None:
    """A sign-in redirect is entered and left, twice, and it is still not a tab
    anybody worked in. Every gesture on it moved the operator somewhere else,
    which is the same rule `checks.work_only` uses to strike one out of a job."""
    sitting = [
        _at(WMS, 100),
        _at(IDP, 110, moved_to=WMS),
        _at(WMS, 120),
        _at(IDP, 130, moved_to=WMS),
        _at(WMS, 140),
    ]

    assert worked_in_both(sitting, gap=600) == set()


def test_a_pause_longer_than_the_browsers_own_tail_is_two_doings() -> None:
    """`gap` is the caller's, and the caller passes `K_SITTING_GAP_S` -- tied to
    the extension's `K_TAIL_TTL_S`, because two gestures further apart than the
    browser's tail can never be matched in one shape however related they are."""
    apart = [_at(MAIL, 100), _at(WMS, 110), _at(MAIL, 9_000), _at(WMS, 9_010)]

    assert worked_in_both(apart, gap=600) == set()


def test_this_deployments_own_console_is_not_a_second_system() -> None:
    # The operator had the console open while working. `admit` refuses the
    # apparatus at the door and `work_only` strikes it from a job; this is the
    # same judgment one layer earlier.
    ours = "http://localhost:3000"
    sitting = [_at(ours, 100), _at(WMS, 110), _at(ours, 120), _at(WMS, 130)]

    assert worked_in_both(sitting, gap=600, ours=frozenset({"localhost:3000"})) == set()
