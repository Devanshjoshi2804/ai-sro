"""Reading one gesture, and reading a day of them.

Ported from `new_agent_arch/tests/test_intents.py` -- every test there that
puts a question to a model is here; the two that do not are in
`tests/unit/domain/rig/test_reading.py`. The loop's own tests are new: the rig
had none, and three of the four things it learned about the loop were learned
in production.
"""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.observation.read_gesture import (
    READING_LIMIT,
    ReadGestures,
    read_gesture,
    read_new_gestures,
)
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.domain.chat.reading import ChatReading
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.gesture import Action, Body, Call, Gesture, Intent, Target, ValueSeen
from sro.domain.observation.reading import INSTRUCTIONS, INTENT_SCHEMA, TAIL
from sro.domain.observation.redaction import is_secret_name
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.identifiers import BatchId, DeviceId, PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker, FakeBlobStore, FakeClock, FakeUnitOfWork

MODEL = "gemini-3.8-flash"
TENANT = TenantId("acme")
OTHER = TenantId("other-corp")
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
NO_CAP = -1.0


def _answer(**data: object) -> Answer:
    base: dict[str, object] = {
        "act": "typed a client code",
        "object": "client",
        "system": "http://127.0.0.1:63319",
        "page": "orders",
        "values_seen": [{"field": "clientCode", "value": "ACME-4471"}],
        "continues": None,
        "confidence": "high",
        "why": "the field is labelled Client Code",
    }
    return Answer(data={**base, **data}, in_tokens=400, out_tokens=60, cost_usd=0.0005)


async def test_a_gesture_becomes_an_intent() -> None:
    gesture = _gestures()[0]
    asker = FakeAsker(_answer())

    intent = await read_gesture(gesture, tail=[], asker=asker, model=MODEL)

    assert intent.gesture_id == gesture.id
    assert intent.act == "typed a client code"
    assert intent.values_seen[0].field == "clientCode"
    assert intent.confidence == "high"


async def test_the_cost_of_the_call_lands_on_the_intent() -> None:
    asker = FakeAsker(_answer())

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.in_tokens == 400
    assert intent.out_tokens == 60
    assert intent.cost_usd > 0
    assert intent.model == MODEL


async def test_a_refusal_leaves_an_intent_that_says_so() -> None:
    """A failed reading must not lose the gesture; the window still gets it."""
    asker = FakeAsker(Answer(error="503 from the model"))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.act is None
    assert intent.error == "503 from the model"


async def test_only_the_last_eight_intents_are_carried_as_context() -> None:
    tail = [Intent(gesture_id=f"ges_{n}", tenant="new", act=f"did {n}") for n in range(20)]
    asker = FakeAsker(_answer())

    await read_gesture(_gestures()[0], tail=tail, asker=asker, model=MODEL)

    sent = asker.asked[0]["evidence"]
    assert isinstance(sent, str)

    assert "did 19" in sent
    assert "did 12" in sent
    assert "did 11" not in sent
    assert TAIL == 8


async def test_a_thin_target_is_asked_about_with_a_picture() -> None:
    thin_one = next(g for g in _gestures() if g.action.secret)  # no name, no label
    asker = FakeAsker(_answer(), _answer())

    await read_gesture(thin_one, tail=[], asker=asker, model=MODEL, image=b"PNG")

    assert asker.asked[0]["image"] == b"PNG"


async def test_a_named_target_is_asked_about_without_one() -> None:
    named = next(g for g in _gestures() if g.action.kind == "select")
    asker = FakeAsker(_answer())

    await read_gesture(named, tail=[], asker=asker, model=MODEL, image=b"PNG")

    assert asker.asked[0]["image"] is None


async def test_no_credential_value_reaches_the_prompt() -> None:
    """The fixture's own secret gesture already has value:null in raw JSON, so
    it cannot prove this on its own -- there is nothing in it to leak. Mutate a
    real value into a target's `secret` flag after parsing instead, which is
    the one route the wire's own validator does not re-check, and is exactly
    why trim() holds this rule for itself."""
    ordinary = next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)
    real_value = ordinary.action.value
    assert real_value  # the fixture must actually carry something to leak
    target = ordinary.action.target
    assert target is not None

    ordinary.action = replace(ordinary.action, target=replace(target, secret=True))
    asker = FakeAsker(_answer())

    await read_gesture(ordinary, tail=[], asker=asker, model=MODEL)

    sent = asker.asked[0]["evidence"]
    assert isinstance(sent, str)
    assert real_value not in sent
    assert '"value": null' in sent


async def test_a_stray_type_in_values_seen_does_not_crash_the_reading() -> None:
    """The schema is advisory. A model returning values_seen as anything but a
    list must not take the gesture down with it.

    A string here proved nothing: iterating it yields characters, and the
    per-entry dict guard downstream drops every one of them -- so the outer
    `isinstance(seen_list, list)` could be deleted with this green. One
    container checked and its sibling walked past. The values that
    discriminate are the ones that are not iterable at all, and the mapping
    that iterates as its own keys.
    """
    for stray in (7, None, True, {"clientCode": "ACME-4471"}, "none that I can see"):
        asker = FakeAsker(_answer(values_seen=stray))

        intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

        assert intent.values_seen == [], stray
        assert intent.error is None, stray


async def test_a_wrong_typed_field_does_not_poison_a_later_gestures_reading() -> None:
    """A list where act should be a string used to reach one_line() unguarded,
    and crash on the NEXT gesture that pulled this intent into its tail."""
    asker = FakeAsker(_answer(act=["typed", "something"]))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)
    assert intent.act is None  # unusable, not fabricated

    downstream = FakeAsker(_answer())
    await read_gesture(_gestures()[1], tail=[intent], asker=downstream, model=MODEL)


async def test_a_wrong_typed_values_seen_entry_is_dropped_not_coerced() -> None:
    """A non-str field is unusable (dropped, not str()'d into a fake one); a
    non-str value is treated as unseen ("") rather than fabricated."""
    asker = FakeAsker(
        _answer(
            values_seen=[
                {"field": 123, "value": "should be dropped, field is not a string"},
                {"field": "qty", "value": 7},
                {"field": "clientCode", "value": "ACME-4471"},
            ]
        )
    )

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert [seen.field for seen in intent.values_seen] == ["qty", "clientCode"]
    assert intent.values_seen[0].value == ""
    assert intent.values_seen[1].value == "ACME-4471"


async def test_an_undeclared_confidence_value_is_unusable() -> None:
    """confidence is declared enum ["high","medium","low"] but nothing checked
    it; a model returning "very high" must not store it verbatim."""
    asker = FakeAsker(_answer(confidence="very high"))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.confidence is None


async def test_a_reading_it_could_not_price_says_so() -> None:
    """Deleting the unpriced hop in read_gesture left the whole suite green."""
    asker = FakeAsker(Answer(data={"act": "did a thing", "why": "because"}, unpriced=True))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.unpriced is True


async def test_a_credential_the_model_echoed_back_is_never_stored() -> None:
    """The third place values_seen went unguarded, and the only one that
    reaches storage: save_intent writes this verbatim and the gestures route
    serves it back. The field name is kept; the value is not.

    The field is deliberately not called "password": with that name this passed
    on `is_secret_name` alone, and deleting the `is_secret(gesture)` half -- the
    branch this test exists for -- left the suite green. "Employee Code" is a
    real WMS label that no name rule flags, so the only thing that blanks it is
    the gesture itself being a credential field.
    """
    gesture = next(g for g in _gestures() if g.action.secret)
    assert not is_secret_name("Employee Code")  # nothing else can blank this
    asker = FakeAsker(_answer(values_seen=[{"field": "Employee Code", "value": "hunter2"}]))

    intent = await read_gesture(gesture, tail=[], asker=asker, model=MODEL)

    assert [seen.value for seen in intent.values_seen] == [""]
    assert [seen.field for seen in intent.values_seen] == ["Employee Code"]


async def test_a_credential_named_by_the_model_is_dropped_on_a_public_gesture() -> None:
    """The gesture is not secret -- a login click never is -- so `hide` is
    False and the field name is the only thing that says what this holds."""
    gesture = next(g for g in _gestures() if not g.action.secret)
    assert not is_secret(gesture)
    asker = FakeAsker(_answer(values_seen=[{"field": "password", "value": "hunter2"}]))

    intent = await read_gesture(gesture, asker=asker, model=MODEL, tail=[])

    assert [seen.value for seen in intent.values_seen] == [""]
    assert [seen.field for seen in intent.values_seen] == ["password"]


async def test_the_model_is_told_what_to_do_and_given_a_response_schema() -> None:
    """`INSTRUCTIONS = ""` and `INTENT_SCHEMA = {}` both left the suite green.

    Nothing asserted that the prompt or the schema ever reach the API. For a
    system whose measured claim is that citation-forcing cut hallucinated steps
    from 21% to under 7.5%, the two rules that force it -- do not guess at a
    value you cannot see, do not describe the HTML -- arriving at the model is
    the claim itself, not a detail.
    """
    asker = FakeAsker(_answer())

    await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    asked = asker.asked[0]
    instructions = asked["instructions"]
    assert isinstance(instructions, str)
    schema = asked["schema"]
    assert isinstance(schema, dict)

    assert instructions == INSTRUCTIONS
    assert "Do not guess at a value you cannot see" in instructions
    assert "Do not describe the HTML" in instructions

    assert schema == INTENT_SCHEMA
    assert set(schema["required"]) == {"act", "why"}
    assert set(schema["properties"]) >= {
        "act",
        "object",
        "values_seen",
        "continues",
        "confidence",
        "why",
    }


async def test_an_empty_continues_is_not_a_continuation() -> None:
    """The schema itself says "empty unless it continues the last doing", so
    `""` is what a model returns for most gestures. Stored verbatim it is
    neither a link nor an absence, and `continues` is what the mining pass
    walks to join gestures into a workflow."""
    asker = FakeAsker(_answer(continues=""))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.continues is None


async def test_one_gesture_is_one_call() -> None:
    """A3's whole claim. Batching stream items into a shared call degrades each
    through semantic interference; the saving is small and the cost is per-item
    quality. A reading that asked twice -- a retry, a second pass for the
    picture -- would double the most-billed path in the system."""
    asker = FakeAsker(_answer(), _answer())

    await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert len(asker.asked) == 1


async def test_the_redaction_marker_reaches_the_prompt_as_itself() -> None:
    """`ensure_ascii=False`, and it is not cosmetic.

    The marker is «redacted». The default escaping writes it into the prompt as
    \\u00abredacted\\u00bb -- a form nothing else in this system uses -- so the
    model was asked to understand a marker written one way here and another way
    everywhere else, and a reviewer grepping stored prompts for it found
    nothing.
    """
    gesture = _gestures()[0]
    gesture.requests = [
        Call(
            method="POST",
            url="http://127.0.0.1:63319/api/login",
            request_body=Body(
                text='{"password": "hunter2"}', size_bytes=23, mime_type="application/json"
            ),
        )
    ]
    asker = FakeAsker(_answer())

    await read_gesture(gesture, tail=[], asker=asker, model=MODEL)

    sent = asker.asked[0]["evidence"]
    assert isinstance(sent, str)
    assert REDACTED in sent
    assert "\\u00ab" not in sent


async def _stored(tenant: TenantId) -> tuple[FakeUnitOfWork, list[Gesture]]:
    uow = FakeUnitOfWork()
    day = _gestures(tenant.value)
    await uow.gestures.add_gestures(tuple(day))
    return uow, day


def _answers(how_many: int) -> list[Answer]:
    return [_answer() for _ in range(how_many)]


def _evidence(asker: FakeAsker, nth: int) -> str:
    sent = asker.asked[nth]["evidence"]
    assert isinstance(sent, str)
    return sent


async def test_every_unread_gesture_of_this_tenant_gets_one_reading() -> None:
    uow, day = await _stored(TENANT)
    asker = FakeAsker(*_answers(len(day)))

    written = await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP
    )

    assert written == len(day)
    assert len(asker.asked) == len(day)
    assert len(await uow.gestures.intents_for(TENANT)) == len(day)


async def test_a_second_tenants_gestures_are_not_read_on_this_ones_bill() -> None:
    """Scoped, because the reading is what costs money: a second tenant in one
    database had this loop paying for gestures no pass of ours will ever mine,
    and filing intents under their tenant on our bill."""
    uow, day = await _stored(TENANT)
    other = _gestures(OTHER.value)
    await uow.gestures.add_gestures(tuple(other))
    asker = FakeAsker(*_answers(len(day)))

    written = await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP
    )

    assert written == len(day)
    assert len(asker.asked) == len(day)
    # Not one reading filed under theirs, and every gesture of theirs still
    # unread and still stored -- capture is not what the scope stops.
    assert await uow.gestures.intents_for(OTHER) == ()
    assert len(await uow.gestures.unread(OTHER, limit=100)) == len(other)


async def test_a_reading_that_came_back_broken_is_never_asked_again() -> None:
    """An intent row means a reading happened, whatever came back in it.

    An error, and an answer whose `act` was the wrong type and got nulled, are
    both rows: the model was asked, it answered, and it was billed. Re-asking
    the same evidence with the same prompt bills again for the same likely
    answer. What such a row gets instead is to be visible.
    """
    uow, day = await _stored(TENANT)
    broken = [Answer(error="503 from the model"), _answer(act=["typed", "something"])]
    asker = FakeAsker(*broken, *_answers(len(day) - 2))

    await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP
    )
    stored = await uow.gestures.intents_for(TENANT)
    assert [intent for intent in stored if intent.error or intent.act is None]

    again = FakeAsker(*_answers(len(day)))
    written = await read_new_gestures(
        uow, tenant_id=TENANT, asker=again, model=MODEL, now=NOW, cap_usd=NO_CAP
    )

    assert written == 0
    assert again.asked == []


async def test_the_cap_stops_the_reading_before_it_asks_anything() -> None:
    """Reading stops; capture does not. The evidence is still stored, so
    raising the cap tomorrow reads what today declined -- and a cap checked
    per gesture instead of before the loop is a cap that has already paid for
    the gesture it stops on."""
    uow, day = await _stored(TENANT)
    asker = FakeAsker(*_answers(len(day)))

    written = await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=0.0
    )

    assert written == 0
    assert asker.asked == []
    assert len(await uow.gestures.unread(TENANT, limit=100)) == len(day)


async def test_two_loops_over_one_tenant_do_not_bill_the_same_gesture_twice() -> None:
    """Two concurrent callers both select the same unread gestures before
    either writes an intent, so every gesture in the race window is asked --
    and billed -- twice, while the replacing write leaves only one cost row.
    One reading loop fires per ingest, so two batches arriving together is
    enough."""
    uow, day = await _stored(TENANT)
    asker = FakeAsker(*_answers(len(day) * 2))

    await asyncio.gather(
        read_new_gestures(uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP),
        read_new_gestures(uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP),
    )

    assert len(asker.asked) == len(day)


async def test_two_tenants_read_at_the_same_time_rather_than_in_turn() -> None:
    """Keyed by tenant, not by the bare word "reading". A single global name
    makes two DIFFERENT tenants take turns, which is nothing but a queue: the
    bake-off ran five models over five copies of one day and a global lock
    turned an hour of parallel work into five hours of serial work.

    Under one lock the first loop runs to completion before the second starts,
    so the first two questions asked both belong to the same tenant.
    """
    uow, day = await _stored(TENANT)
    await uow.gestures.add_gestures(tuple(_gestures(OTHER.value)))
    order: list[str] = []

    class Recording:
        """A FakeAsker that writes down whose turn it was."""

        def __init__(self, tenant: str) -> None:
            self._tenant = tenant

        async def ask(self, **_: object) -> Answer:
            await asyncio.sleep(0)
            order.append(self._tenant)
            return _answer()

    await asyncio.gather(
        read_new_gestures(
            uow,
            tenant_id=TENANT,
            asker=Recording(TENANT.value),
            model=MODEL,
            now=NOW,
            cap_usd=NO_CAP,
        ),
        read_new_gestures(
            uow, tenant_id=OTHER, asker=Recording(OTHER.value), model=MODEL, now=NOW, cap_usd=NO_CAP
        ),
    )

    assert len(order) == len(day) * 2
    assert set(order[:2]) == {TENANT.value, OTHER.value}


async def test_each_reading_is_committed_before_the_next_one_is_asked() -> None:
    """A loop that raises on gesture 50 has already been billed for 49. One
    commit at the end would roll those back, leave them unread, and ask -- and
    pay -- for them again on the next pass."""
    uow, day = await _stored(TENANT)
    asker = FakeAsker(*_answers(len(day)))

    await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP
    )

    assert uow.commits == len(day)


async def test_a_gesture_is_read_against_what_its_streams_last_readings_said() -> None:
    """The tail is what `continues` is decided from, so a reading written
    earlier in this same loop has to be in the next gesture's context -- and a
    reading of the operator's OTHER tab must not be, however recent it is.

    The fixture is one stream, so the scoping is invisible without a second:
    dropping `other.stream_id == gesture.stream_id` from `_tail_for` left the
    whole suite green while leaking another tab's readings into every prompt
    and billing for the tokens.
    """
    uow, day = await _stored(TENANT)
    other_tab = replace(day[0], id="ges_other_tab", stream_id="dev_other", at=day[0].at - 1)
    await uow.gestures.add_gestures((other_tab,))
    asker = FakeAsker(
        _answer(act="counted pallets in the other tab"),
        _answer(act="opened the client form"),
        *_answers(len(day)),
    )

    await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP
    )

    read = [_evidence(asker, nth) for nth in range(len(asker.asked))]
    # The other tab is read first -- it is the oldest -- and belongs in nobody
    # else's context.
    assert not any("counted pallets in the other tab" in sent for sent in read)
    assert "opened the client form" not in read[1]
    assert "opened the client form" in read[2]


async def test_one_pass_reads_no_more_than_its_limit() -> None:
    """A pass that asks the model thousands of times before returning is a pass
    nothing can stop, and a drain calls this repeatedly instead. Both halves
    are load-bearing: the number, and it actually reaching the repository."""
    uow, day = await _stored(TENANT)
    assert len(day) > 2
    asker = FakeAsker(*_answers(len(day)))

    written = await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP, limit=2
    )

    assert written == 2
    assert len(asker.asked) == 2
    assert READING_LIMIT == 200


class _Collapses:
    """An asker that answers a few times and then does not come back at all.

    `Asker` promises no such thing as never raising: a transport gives up, a
    client raises on a malformed envelope, and today's adapter catching
    `Exception` itself is that adapter's choice rather than the port's rule.
    """

    def __init__(self, after: int) -> None:
        self.after = after
        self.asked = 0

    async def ask(self, **_: object) -> Answer:
        await asyncio.sleep(0)
        self.asked += 1
        if self.asked > self.after:
            raise RuntimeError("the transport gave up")
        return _answer()


async def test_a_call_that_raised_is_never_filed_as_a_reading_that_happened() -> None:
    """Both billed and hidden is the one outcome this design refuses.

    Swallowing the exception and filing `intent_from(None, ...)` writes an
    `act=None`, `error=None`, `cost_usd=0.0` row for a call that may well have
    been billed -- and because an intent row exists, the never-retried rule
    then guarantees it is never asked again. The refusal test cannot catch it:
    its asker RETURNS an `Answer(error=...)` and never raises, so the two paths
    never meet.

    Propagating instead loses nothing: every reading before it is already
    committed, and the gesture it died on stays unread and is read next pass.
    """
    uow, day = await _stored(TENANT)
    assert len(day) > 2

    with pytest.raises(RuntimeError):
        await read_new_gestures(
            uow, tenant_id=TENANT, asker=_Collapses(after=2), model=MODEL, now=NOW, cap_usd=NO_CAP
        )

    assert len(await uow.gestures.intents_for(TENANT)) == 2
    assert uow.commits == 2
    assert len(await uow.gestures.unread(TENANT, limit=100)) == len(day) - 2


async def test_a_write_gestures_reading_folds_in_the_tails_values() -> None:
    """The real gap a harsh look at real captured data found: a save click's
    own reading names one field, and the fields typed just before it in the
    same doing -- already readings sitting in `tail` -- were being left off
    rather than folded in."""
    save = replace(
        _gestures()[0],
        id="ges_save",
        action=Action(kind="click", at=1.0),
        requests=[Call(method="POST", url="http://127.0.0.1:63319/api/save", status=201)],
    )
    tail = [
        Intent(
            gesture_id="ges_0",
            tenant="new",
            values_seen=[ValueSeen(field="code", value="DSS")],
        )
    ]
    asker = FakeAsker(_answer(values_seen=[{"field": "customerType", "value": "CCD"}]))

    intent = await read_gesture(save, tail=tail, asker=asker, model=MODEL)

    assert {seen.field: seen.value for seen in intent.values_seen} == {
        "code": "DSS",
        "customerType": "CCD",
    }


async def test_a_thin_gesture_is_asked_about_with_its_real_picture() -> None:
    """`read_new_gestures` wired to a blob store: a thin gesture (an icon-only
    button, a shadow-dom host -- the real shapes a genuinely unlabeled target
    takes) is asked about with the picture the recorder took of it, joined the
    same way `ReadShots` joins a mined job's evidence tab."""
    tenant = TenantId("new")
    batch_id = "bat-thin"
    device = DeviceId("dev-thin")
    operator = PrincipalId("clerk@acme.test")
    at = 1789000000.0
    day = NOW.date().isoformat()
    key = f"{tenant.value}/{operator}/{day}/{batch_id}.ndjson"
    uri = f"s3://sro-artifacts/{key}"
    shots_prefix = f"{tenant.value}/{operator}/{day}/{batch_id}/screenshot"

    payload = (
        json.dumps(
            {
                "kind": "gesture",
                "gesture": {"kind": "click", "at": at, "url": "https://wms.test/portal"},
            }
        ).encode()
        + b"\n"
    )

    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    blobs.objects[key] = payload
    blobs.objects[f"{shots_prefix}/00000.png"] = b"PNG-BYTES"
    await uow.observations.add(
        ObservationBatch(
            id=BatchId(batch_id),
            tenant_id=tenant,
            device_id=device,
            principal_id=operator,
            mode=CaptureMode.PASSIVE,
            started_at=NOW,
            ended_at=NOW + timedelta(minutes=1),
            received_at=NOW,
            uri=uri,
            event_count=1,
            byte_count=len(payload),
        )
    )
    thin_gesture = Gesture(
        id="ges_thin",
        tenant=tenant.value,
        stream_id="str-1",
        batch_id=batch_id,
        at=at,
        url="https://wms.test/portal",
        system="https://wms.test",
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=at, target=Target(tag="img")),
    )
    await uow.gestures.add_gestures((thin_gesture,))
    asker = FakeAsker(_answer())

    await read_new_gestures(
        uow, tenant_id=tenant, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP, blobs=blobs
    )

    assert asker.asked[0]["image"] == b"PNG-BYTES"


async def test_with_no_blob_store_a_thin_gesture_is_asked_about_without_a_picture() -> None:
    """Optional and, missing, changes nothing: every gesture is read exactly
    as it was before this was wired in."""
    uow, day = await _stored(TENANT)
    asker = FakeAsker(*_answers(len(day)))

    await read_new_gestures(
        uow, tenant_id=TENANT, asker=asker, model=MODEL, now=NOW, cap_usd=NO_CAP
    )

    assert all(asked["image"] is None for asked in asker.asked)


# --- the door: ReadGestures, POST /v1/gestures/read -------------------------


def _ctx(tenant: TenantId = TENANT) -> RequestContext:
    return RequestContext(tenant_id=tenant, principal_id=PrincipalId("operator"))


def _door(
    uow: FakeUnitOfWork,
    *,
    asker: FakeAsker | None,
    clock: FakeClock | None = None,
    model: str = MODEL,
    cap_usd: float = NO_CAP,
) -> ReadGestures:
    # `hand_out`, as a container hands one out: strict, and not yet entered. A
    # door that read a repository without opening its own session would be an
    # AttributeError here rather than a green test and a 500 in production.
    return ReadGestures(
        uow.hand_out(), asker=asker, model=model, clock=clock or FakeClock(NOW), cap_usd=cap_usd
    )


async def _billed(uow: FakeUnitOfWork, *, cost_usd: float, at: datetime) -> None:
    await uow.chats.record(
        ChatReading(id=f"cht_{cost_usd}", tenant=TENANT.value, at=at.isoformat(), cost_usd=cost_usd)
    )


async def test_no_asker_refuses_before_anything_is_read() -> None:
    uow, _ = await _stored(TENANT)

    with pytest.raises(AskerUnavailable):
        await _door(uow, asker=None).execute(_ctx())

    assert uow.commits == 0, "a refused door opened and committed a transaction"


async def test_over_the_cap_refuses_and_says_which_number_stopped_it() -> None:
    uow, day = await _stored(TENANT)
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))
    asker = FakeAsker(*_answers(len(day)))

    with pytest.raises(OverCap) as refused:
        await _door(uow, asker=asker, cap_usd=5.0).execute(_ctx())

    assert "5.0100" in str(refused.value)
    assert "5.00" in str(refused.value)
    assert asker.asked == [], "a call was made after the door should have refused"


async def test_a_refusal_at_the_door_reads_nothing() -> None:
    uow, day = await _stored(TENANT)
    await _billed(uow, cost_usd=5.01, at=NOW.replace(hour=10))
    asker = FakeAsker(*_answers(len(day)))

    with pytest.raises(OverCap):
        await _door(uow, asker=asker, cap_usd=5.0).execute(_ctx())

    assert await uow.gestures.intents_for(TENANT) == ()


async def test_a_door_that_runs_reads_every_unread_gesture_and_says_how_many() -> None:
    uow, day = await _stored(TENANT)
    asker = FakeAsker(*_answers(len(day)))

    read = await _door(uow, asker=asker).execute(_ctx())

    assert read == len(day)
    assert len(await uow.gestures.intents_for(TENANT)) == len(day)


async def test_the_tenant_read_is_the_ones_on_the_context_and_never_the_stores() -> None:
    """Two tenants, because a door that read the tenant off anything but `ctx`
    passes every other assertion in this file. Asked for `OTHER`, it reads
    `OTHER`'s day and never touches `TENANT`'s."""
    uow, _ = await _stored(TENANT)
    other_day = _gestures(OTHER.value)
    await uow.gestures.add_gestures(tuple(other_day))
    asker = FakeAsker(*_answers(len(other_day)))

    read = await _door(uow, asker=asker).execute(_ctx(OTHER))

    assert read == len(other_day)
    assert await uow.gestures.intents_for(TENANT) == ()
    assert len(await uow.gestures.intents_for(OTHER)) == len(other_day)


async def test_the_model_asked_is_the_one_this_deployment_configured() -> None:
    uow, day = await _stored(TENANT)
    asker = FakeAsker(*_answers(len(day)))

    await _door(uow, asker=asker, model="gemini-3.1-flash-preview").execute(_ctx())

    assert [one["model"] for one in asker.asked] == ["gemini-3.1-flash-preview"] * len(day)


async def test_the_cap_is_checked_against_the_doors_own_clock() -> None:
    """23:00, one hour before a midnight the same way `test_mine_pass.py`
    measures it: `over_cap` sums the day from the midnight before `now`, so an
    hour's advance moves this into the next day and out of reach of the spend
    planted below."""
    edge = datetime(2026, 9, 7, 23, 0, tzinfo=UTC)
    uow, day = await _stored(TENANT)
    await _billed(uow, cost_usd=5.01, at=edge.replace(hour=10))
    clock = FakeClock(edge)

    with pytest.raises(OverCap):
        await _door(uow, asker=FakeAsker(*_answers(len(day))), clock=clock, cap_usd=5.0).execute(
            _ctx()
        )

    clock.advance(3600)

    assert await _door(
        uow, asker=FakeAsker(*_answers(len(day))), clock=clock, cap_usd=5.0
    ).execute(_ctx())
