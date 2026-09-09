"""Ported from `new_agent_arch/tests/test_window.py`, all 19, names unchanged.

Eight of them call `pack`, which subtracts the prompt's fixed cost and therefore
imports `PROMPT_OVERHEAD_TOKENS` from `sro.domain.skill.umbrella`. That module
landed with the umbrella prompt, so all nineteen run.

Two more are added here rather than ported, each closing a hole the rig's own
suite had: `test_evidence_is_measured_the_way_the_prompt_ships_it` and
`test_a_gesture_that_exactly_fills_the_cap_is_kept_whole`. Both are named in
their own docstrings for what they pin.
"""

import copy
import json
from dataclasses import replace

from sro.domain.observation.gesture import Gesture, Intent, Kind, ValueSeen
from sro.domain.observation.window import (
    K_MAX_GESTURE_TOKENS,
    K_MAX_ITEMS,
    K_MAX_TEXT_CHARS,
    K_MIN_GESTURES,
    K_WINDOW_TOKENS,
    Packed,
    Window,
    arrange,
    as_evidence,
    evidence_tokens,
    pack,
    strength,
    tokens,
)
from sro.domain.skill.umbrella import build_prompt
from tests.unit.domain.rig.conftest import gestures as _gestures


def _map(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _seq(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def test_tokens_is_a_length_not_a_guess() -> None:
    assert tokens("") == 0
    assert tokens("a" * 400) == 100


MEASURED_RATIO = 1.697
"""What `tokens()` under-counts real tokens by, on real evidence.

507 gestures of Blue Yonder capture, 481,566 characters: `tokens()` returned
120,438 and Gemini counted 204,333. 2.36 characters to the token, not 4.
"""

PRICE_BOUNDARY = 200_000
"""Where Gemini 3.1 Pro's input price doubles. An external fact about a
supplier, which is what makes it worth an assertion: every other number in
`window.py` is a bound on another number in `window.py`."""


def test_the_budget_stays_under_the_price_boundary_in_real_tokens() -> None:
    """The only assertion `K_WINDOW_TOKENS` has that is not derived from it.

    `NEARLY_FULL_KB` (test_mine.py:162) is computed FROM it, and
    `test_a_window_packed_to_the_budget_still_fits_the_budget` asserts
    `shipped <= K_WINDOW_TOKENS` -- both self-referential, and both counted
    with the same under-reading `tokens()`. So the 200,000 boundary appeared in
    no assertion anywhere, and setting the budget back to 150,000 -- the exact
    value that shipped 204,747 real tokens and cost $2.00 -- passed every gate
    in this repository.

    This is the boundary, not the constant. Raising the budget is allowed; a
    budget whose REAL token count crosses the price line is not, and the ratio
    is the only thing standing between the two.
    """
    assert K_WINDOW_TOKENS * MEASURED_RATIO < PRICE_BOUNDARY, (
        f"{K_WINDOW_TOKENS} estimated is ~{int(K_WINDOW_TOKENS * MEASURED_RATIO)} real tokens, "
        f"over the {PRICE_BOUNDARY} boundary where the price doubles"
    )


def test_evidence_is_measured_the_way_the_prompt_ships_it() -> None:
    """`evidence_tokens` counts an item the way `umbrella.build_prompt` writes
    it -- inside a list, at indent=1, with the text left alone -- and that is
    an equality with another module rather than a preference.

    Measuring it compact passed every other test in this file and under-counted
    the real acme window by 17.6% -- 22,593 counted against 26,566 shipped --
    which on a window filled to K_WINDOW_TOKENS means ~177,000 tokens over the
    200K boundary where the input price doubles, silently. So the assertion is
    against the prompt that actually goes out: the rendering measured has to be
    the rendering shipped, character for character, and the count has to be
    that rendering's.

    The value carries non-ASCII on purpose. `ensure_ascii=False` is the half of
    the shape a directional "bigger than compact" assertion cannot see: the
    default escapes every one of these characters to six, so a window of German
    or Japanese field labels is over-counted against a prompt that ships them
    whole.
    """
    gesture = copy.deepcopy(_gestures()[0])
    gesture.action = replace(gesture.action, value="ACME-4471 -- Größe · naïve ¥ € ½ Ω")
    evidence = as_evidence(gesture, None)
    item = Packed(gesture.id, gesture.at, evidence, 1.0, evidence_tokens(evidence))

    shipped = build_prompt(Window(items=[item]), {}, [], "")

    block = json.dumps([evidence], indent=1, ensure_ascii=False)
    assert block in shipped, "the shape measured is not the shape the prompt ships"
    assert evidence_tokens(evidence) == tokens(block)


def test_evidence_carries_the_reading_beside_the_gesture() -> None:
    gesture = _gestures()[0]
    intent = Intent(gesture_id=gesture.id, tenant="acme", act="typed a code", why="because")

    evidence = as_evidence(gesture, intent)

    assert evidence["id"] == gesture.id
    assert _map(evidence["intent"])["act"] == "typed a code"
    assert "target" in _map(evidence["gesture"])


def test_a_gesture_with_no_reading_still_enters_the_window() -> None:
    """A failed reading must not remove the evidence from the pass."""
    evidence = as_evidence(_gestures()[0], None)

    assert evidence["intent"] is None
    assert evidence["gesture"]


def test_a_write_and_a_typed_value_are_stronger_than_a_read() -> None:
    gestures = _gestures()
    writing = next(g for g in gestures if any(r.method != "GET" for r in g.requests))
    reading = next(g for g in gestures if not g.requests)

    assert strength(writing, None, set()) > strength(reading, None, set())


def test_a_gesture_that_shares_a_value_across_systems_is_stronger() -> None:
    gesture = _gestures()[0]

    assert strength(gesture, None, {gesture.id}) > strength(gesture, None, set())


def test_no_single_gesture_may_eat_the_window() -> None:
    """Three of eighty-one real gestures held 71% of all request bytes, and two
    individually exceeded the whole budget."""
    gesture = next(g for g in _gestures() if g.requests and g.requests[0].response_body)
    call = gesture.requests[0]
    assert call.response_body is not None
    gesture.requests[0] = replace(
        call, response_body=replace(call.response_body, text="x" * 400_000)
    )

    evidence = as_evidence(gesture, None)

    assert tokens(json.dumps(evidence)) <= K_MAX_GESTURE_TOKENS


def test_the_cap_holds_by_every_route() -> None:
    """The test above passes with the cap deleted: trim() already truncates a
    body to VALUE_CHARS before as_evidence sees it. These are the routes that
    actually reach the cap, each measured past a body-only cap by 15x to 1000x.
    """
    huge = "x" * 4_000_000
    base = next(g for g in _gestures() if g.requests)

    value = copy.deepcopy(base)
    value.action = replace(value.action, value=huge)

    url = copy.deepcopy(base)
    url.url = "https://acme.example/" + huge

    many = copy.deepcopy(base)
    many.requests = [copy.deepcopy(base.requests[0]) for _ in range(2_000)]

    for name, gesture in (("value", value), ("url", url), ("calls", many)):
        size = tokens(json.dumps(as_evidence(gesture, None)))
        assert size <= K_MAX_GESTURE_TOKENS, f"{name}: {size}"

    # Size alone cannot tell a bounded body from a collapsed one: with the
    # count-bounding tier deleted this test still passed, because the skeleton
    # backstop absorbed the swamped gesture and dropped `calls` entirely. A
    # gesture that made two thousand calls should still say it made calls.
    assert _map(as_evidence(many, None)["gesture"])["calls"]

    # Model output, and nothing upstream bounds its length.
    loud = Intent(
        gesture_id=base.id,
        tenant="acme",
        act=huge,
        object=huge,
        page=huge,
        why=huge,
        confidence="high",
        values_seen=[ValueSeen(field=huge, value=huge)],
    )
    size = tokens(json.dumps(as_evidence(base, loud)))
    assert size <= K_MAX_GESTURE_TOKENS, f"intent: {size}"


def _on_the_cap(gesture: Gesture, values: int, value_chars: int = 100) -> dict[str, object] | None:
    """This gesture's evidence rendered at exactly K_MAX_GESTURE_TOKENS, or
    None when this shape cannot be made to land there.

    Grown rather than hand-written, because the fixture's own size is nobody's
    constant and a hard-coded gesture would stop sitting on the boundary the
    first time `trim` changed. The caller's knob -- `values`, or the number of
    calls -- gets the body within 400 characters of the cap; `why` is clipped
    at K_MAX_TEXT_CHARS, so 401 consecutive lengths are reachable from there
    and one of them is the character the cap is on.
    """

    def reading(why: int) -> Intent:
        return Intent(
            gesture_id=gesture.id,
            tenant="acme",
            act="typed a code",
            why="w" * why,
            values_seen=[ValueSeen(field=f"f{n}", value="v" * value_chars) for n in range(values)],
        )

    # tokens() is len // 4, so this is the shortest body that reads as the cap.
    target = K_MAX_GESTURE_TOKENS * 4
    short = target - len(json.dumps(as_evidence(gesture, reading(0)), ensure_ascii=False))
    if not 0 <= short <= K_MAX_TEXT_CHARS:
        return None
    return as_evidence(gesture, reading(short))


def test_a_gesture_that_exactly_fills_the_cap_is_kept_whole() -> None:
    """The boundary the ladder is written on, which nothing else here stands
    on: every other cap test is far over it, so `<= K_MAX_GESTURE_TOKENS`
    survived being `<` untouched. They differ on exactly one input -- the
    gesture that fits with nothing to spare -- and under `<` that gesture is
    truncated for being the size it is allowed to be, losing every call's
    detail and telling the model it was cut.
    """
    gesture = copy.deepcopy(_gestures()[0])

    evidence = None
    for values in range(200):
        evidence = _on_the_cap(gesture, values)
        if evidence is not None:
            break

    assert evidence is not None, "no reading of this fixture lands on the cap"
    assert tokens(json.dumps(evidence, ensure_ascii=False)) == K_MAX_GESTURE_TOKENS
    assert "truncated" not in evidence, "a gesture exactly at the cap is under it"


def test_a_gesture_that_exactly_fills_the_cap_once_stripped_keeps_every_call() -> None:
    """The same boundary one tier down, where the cost of getting it wrong is
    an item rather than a detail: a body that lands on the cap after its calls
    are stripped is under the cap, so the count-bounding tier is not reached
    and all of them survive. Under `<` it is, and five of forty-five calls
    disappear from a gesture the evidence says was only detail-trimmed.
    """
    base = next(g for g in _gestures() if g.requests)

    evidence, made = None, 0
    for made in range(1, 400):
        gesture = copy.deepcopy(base)
        gesture.requests = [copy.deepcopy(base.requests[0]) for _ in range(made)]
        found = _on_the_cap(gesture, 0)
        # Tier one lands on the cap too, at a smaller count; what is wanted
        # here is the body that got there by losing its detail and no items.
        if (
            found is not None
            and found.get("truncated")
            and len(_seq(_map(found["gesture"])["calls"])) == made
        ):
            evidence = found
            break

    assert evidence is not None, "no count of calls lands this fixture on the cap once stripped"
    assert tokens(json.dumps(evidence, ensure_ascii=False)) == K_MAX_GESTURE_TOKENS
    assert len(_seq(_map(evidence["gesture"])["calls"])) == made, "nothing was count-bounded"


def test_a_gesture_that_exactly_fills_the_cap_once_counted_back_is_not_collapsed() -> None:
    """The same boundary at the last tier, where getting it wrong costs the
    whole gesture: a body that lands on the cap after its counts were cut is
    under the cap, so the skeleton backstop is not reached and forty calls and
    forty values survive. Under `<` that same input collapses to `kind` and
    `url` -- 2,000 tokens down to about fifty, every call gone -- and a gesture
    that made four hundred calls arrives saying nothing about calls at all.

    Reached the same way as the tiers above, only with the knobs this tier
    leaves free: everything countable is already bounded at K_MAX_ITEMS here,
    so the coarse adjustment is how long each surviving value is, and `why` is
    still the fine one.
    """
    base = next(g for g in _gestures() if g.requests)
    gesture = copy.deepcopy(base)
    gesture.requests = [copy.deepcopy(base.requests[0]) for _ in range(400)]

    evidence = None
    for value_chars in range(K_MAX_TEXT_CHARS + 1):
        found = _on_the_cap(gesture, K_MAX_ITEMS + 10, value_chars)
        # The skeleton keeps no calls at all, and the tier above keeps all four
        # hundred; forty is this tier and only this tier.
        if found is not None and len(_seq(_map(found["gesture"]).get("calls", []))) == K_MAX_ITEMS:
            evidence = found
            break

    assert evidence is not None, "no value length lands this fixture on the cap once counted back"
    assert tokens(json.dumps(evidence, ensure_ascii=False)) == K_MAX_GESTURE_TOKENS
    assert len(_seq(_map(evidence["gesture"])["calls"])) == K_MAX_ITEMS
    assert len(_seq(_map(evidence["intent"])["values_seen"])) == K_MAX_ITEMS
    assert _map(evidence["gesture"])["target"], "the skeleton keeps no target"


def test_nothing_is_dropped_without_the_evidence_saying_so() -> None:
    """A body that lost five of forty-five calls and still claimed to be whole.
    The umbrella pass cannot tell a gesture that made forty calls from one that
    made forty-five, so a drop has to be visible where it happened."""
    base = next(g for g in _gestures() if g.requests)

    busy = copy.deepcopy(base)
    busy.requests = [copy.deepcopy(base.requests[0]) for _ in range(45)]
    evidence = as_evidence(busy, None)

    # Which tier forty-five calls land in depends on how long each one renders,
    # so a change to the fixture's request moves this test to a different tier
    # without touching a line of window.py -- measured: a 139-char path lands
    # it in tier three, a 214-char path in the skeleton, and a path shorter
    # than the fixture's keeps it in tier one, where nothing is cut and there
    # is nothing to say. Assert the tier, so that shift fails here rather than
    # quietly testing something else under the same name.
    assert evidence["truncated"] is True, "fixture no longer overflows tier one"

    # Forty-five calls fit once their detail is dropped, so none is lost --
    # which is what the ladder is for, and what clipping on the way in skipped.
    assert len(_seq(_map(evidence["gesture"])["calls"])) == 45

    swamped = copy.deepcopy(base)
    swamped.requests = [copy.deepcopy(base.requests[0]) for _ in range(2_000)]
    evidence = as_evidence(swamped, None)

    assert len(_seq(_map(evidence["gesture"])["calls"])) <= K_MAX_ITEMS
    assert evidence["truncated"] is True
    assert tokens(json.dumps(evidence)) <= K_MAX_GESTURE_TOKENS


def test_a_credential_the_model_echoed_back_does_not_reach_the_window() -> None:
    """trim() nulls the typed value. values_seen comes back from the model with
    the field already named, and went into the window unchecked."""
    gesture = copy.deepcopy(_gestures()[0])
    gesture.action = replace(gesture.action, secret=True)
    intent = Intent(
        gesture_id=gesture.id,
        tenant="acme",
        act="typed a password",
        values_seen=[ValueSeen(field="password", value="hunter2")],
    )

    evidence = as_evidence(gesture, intent)

    assert "hunter2" not in json.dumps(evidence)
    seen = _seq(_map(evidence["intent"])["values_seen"])
    assert _map(seen[0])["field"] == "password"


def test_the_middle_of_the_window_keeps_its_order() -> None:
    """Order-invariant representations degrade cross-application reconstruction.
    Only the ends are promoted; a workflow is a sequence."""
    items = [Packed(f"ges_{n}", float(n), {}, float(n), 10) for n in range(40)]
    # Rotated in, because these arrive already in time order: a sort that did
    # nothing at all would return them looking exactly right.
    items = items[17:] + items[:17]

    arranged = arrange(items)
    middle = [item.at for item in arranged[12:-12]]

    assert middle == sorted(middle)
    # The strongest twelve are the ends, dealt alternately to the head and the
    # tail with the tail reversed; the rest keeps its time order. The middle
    # stays sorted under a flipped strength key too, so it is the ends that pin
    # which twelve were promoted.
    assert [item.at for item in arranged] == (
        [39.0, 37.0, 35.0, 33.0, 31.0, 29.0]
        + [float(n) for n in range(28)]
        + [28.0, 30.0, 32.0, 34.0, 36.0, 38.0]
    )


def test_everything_that_fits_is_packed_in_time_order() -> None:
    gestures = _gestures()
    # Reversed, so a pack that returned its input order rather than time order
    # would come back backwards.
    gestures.reverse()

    window = pack(gestures, {}, [], [], "", budget=150_000)

    assert len(window.items) == len(gestures)
    assert [i.at for i in window.items] == sorted(i.at for i in window.items)
    assert window.left_out == []


def test_a_budget_too_small_keeps_the_floor_and_reports_the_rest() -> None:
    """A quiet morning is still read, and what did not fit is named rather
    than silently missing."""
    gestures = _gestures() * 8

    window = pack(gestures, {}, [], [], "", budget=600)

    assert len(window.items) >= min(K_MIN_GESTURES, len(gestures))
    assert len(window.left_out) == len(gestures) - len(window.items)


def test_the_pool_is_favoured_over_equally_strong_new_evidence() -> None:
    """Equal strength, and the pool item is the latest thing in the window, so
    the tie-break on `at` sends it to the back. Only K_POOL_BONUS keeps it.

    The budget has to bite for the slot to be contested at all: the version of
    this test that packed two gestures into 150,000 tokens passed with the
    bonus deleted.
    """
    # The committed fixture has seven gestures; only two -- one "click", one
    # "press" -- carry neither a request nor a type/select/upload bonus, so
    # only those two sit at strength 1.0, equal to the pool item's own raw
    # strength. (The brief's `kind == "click"` filter alone yields exactly
    # one such gesture in this fixture, not the four it assumes; broadened
    # here to the two kinds that share the same baseline strength, which
    # keeps the tie the test depends on.)
    base = [g for g in _gestures() if not g.requests and g.action.kind in ("click", "press")]
    assert len(base) >= 2, "fixture must offer plain clicks/presses to contest with"
    plain = []
    for run in range(K_MIN_GESTURES):
        for gesture in base:
            dup = copy.deepcopy(gesture)
            dup.id = f"{gesture.id}_{run}"
            plain.append(dup)

    pooled = [Packed("ges_pool", max(g.at for g in plain) + 1000.0, {"id": "ges_pool"}, 1.0, 10)]

    # 6_000 (the brief's figure) does not bite against only 50 candidates at
    # ~107 tokens each -- everything fits and nothing is contested. 2_680 sits
    # in the middle of a wide, empirically-checked band (2_650-2_700) where
    # the K_MIN_GESTURES floor is exactly met and the pool slot is genuinely
    # contested.
    window = pack(plain, {}, pooled, [], "", budget=2_680)

    assert window.left_out, "budget must bite, or no slot is contested"
    assert "ges_pool" in {item.gesture_id for item in window.items}


def test_packing_twice_does_not_compound_the_pool_bonus() -> None:
    pooled = [Packed("ges_pool", 0.0, {"id": "ges_pool"}, 1.0, 10)]

    pack(_gestures(), {}, pooled, [], "", budget=150_000)
    pack(_gestures(), {}, pooled, [], "", budget=150_000)

    assert pooled[0].strength == 1.0


def _wrote() -> Gesture:
    """The fixture's one gesture with calls behind it, and they include POSTs."""
    return next(g for g in _gestures() if any(r.method != "GET" for r in g.requests))


def _many(count: int = 60) -> list[Gesture]:
    """Enough gestures for the budget to matter.

    `K_MIN_GESTURES` is 25 and the fixture holds 7, so every window test before
    this one packed everything and never reached the budget branch at all --
    which is why it had seventeen surviving mutants. Cloning the fixture with
    fresh ids is the smallest way to get above the floor.
    """
    made = []
    for n in range(count):
        for gesture in _gestures():
            clone = copy.deepcopy(gesture)
            clone.id = f"{gesture.id}_{n}"
            clone.at = gesture.at + n
            made.append(clone)
            if len(made) == count:
                return made
    return made


def test_what_earns_a_place_in_the_window() -> None:
    """`strength` decides which 6% of a day the model ever sees, and nothing
    pinned its shape. Each clause is asserted as an ORDERING rather than as a
    number: what has to hold is that a gesture which wrote outranks one that
    only read, not that the bonus is 1.0 -- the numbers are tuneable and the
    ranking is the contract.
    """
    plain = copy.deepcopy(_wrote())
    plain.requests = []
    plain.action = replace(plain.action, kind="click")
    base = strength(plain, None, set())

    wrote = copy.deepcopy(_wrote())
    wrote.action = replace(wrote.action, kind="click")
    assert strength(wrote, None, set()) > base, (
        "a gesture that changed something outranks one that looked"
    )

    read_only = copy.deepcopy(wrote)
    read_only.requests = [replace(request, method="GET") for request in read_only.requests]
    assert strength(read_only, None, set()) == base, "and a read earns nothing extra"

    typed = copy.deepcopy(plain)
    kinds: tuple[Kind, ...] = ("type", "select", "upload")
    for kind in kinds:
        typed.action = replace(typed.action, kind=kind)
        assert strength(typed, None, set()) > base, f"{kind} put something into the world"

    sure = Intent(gesture_id=plain.id, tenant="acme", confidence="high")
    unsure = Intent(gesture_id=plain.id, tenant="acme", confidence="low")
    assert strength(plain, sure, set()) > strength(plain, unsure, set()), "a confident reading"

    assert strength(plain, None, {plain.id}) > base, "and evidence that crosses two systems"


def test_the_known_workflows_summary_costs_budget_rather_than_making_it() -> None:
    """The summary goes in the same prompt as the evidence, so its tokens come
    OUT of the room the evidence has. A sign flip here reads as free space and
    packs a window that will not fit -- the exact shape of the failure that
    made a cap not cap."""
    gestures = _many()
    known: list[dict[str, object]] = [
        {"id": f"wfl_{n}", "title": "a job " * 40, "shape_key": ["a"] * 40} for n in range(40)
    ]

    alone = pack(gestures, {}, [], [], "", budget=12_000)
    beside = pack(gestures, {}, [], known, "", budget=12_000)

    assert len(beside.items) < len(alone.items), "the summary took room from the evidence"
    assert beside.left_out, "and what it displaced is named"


def test_a_window_reports_what_it_actually_spent() -> None:
    """`spent` is what a caller checks a budget against, so it has to be the
    sum of what was packed rather than a number of its own."""
    window = pack(_many(), {}, [], [], "", budget=20_000)

    assert window.spent == sum(item.tokens for item in window.items)
    assert window.spent > 0


def test_the_floor_wins_over_the_budget_and_says_what_it_left_out() -> None:
    """K_MIN_GESTURES is the promise that a window is never empty. Below it the
    budget test is not even asked, so a budget of nothing still yields a
    readable window -- and everything the budget refused is named rather than
    disappearing."""
    gestures = _many()

    starved = pack(gestures, {}, [], [], "", budget=0)

    assert len(starved.items) == K_MIN_GESTURES
    assert len(starved.items) + len(starved.left_out) == len(gestures), "nothing vanished"


def test_an_item_that_exactly_fills_the_room_is_packed() -> None:
    """The boundary, which no budget picked at random ever lands on.

    `spent + item.tokens > room` and `>= room` differ on exactly one input: the
    item that fits with nothing to spare. Rejecting it wastes a gesture per
    window for no reason, and a window is the only thing the model ever sees.
    So the budget is computed backwards from the evidence rather than chosen.
    """
    from sro.domain.skill.umbrella import PROMPT_OVERHEAD_TOKENS

    gestures = _many()
    ranked = sorted(
        ((strength(g, None, set()), g.at, evidence_tokens(as_evidence(g, None))) for g in gestures),
        key=lambda item: (-item[0], item[1]),
    )
    wanted = K_MIN_GESTURES + 5
    room = sum(item[2] for item in ranked[:wanted])
    # What `pack` subtracts before it starts: the prompt's fixed cost, and the
    # known-workflow summary, which here is an empty list.
    budget = room + PROMPT_OVERHEAD_TOKENS + tokens(json.dumps([], indent=1, ensure_ascii=False))

    window = pack(gestures, {}, [], [], "", budget=budget)

    assert window.spent == room, "it fits with nothing to spare"
    assert len(window.items) == wanted, "and the one that exactly fits is in"
