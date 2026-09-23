"""What a write plan does with a real captured body.

The fixture is the bytes the warehouse actually received. Measured on the
deployment's own store, 2026-09-15: three demonstrations of `Create a Customer
Type`, 46 keys each, the same key set every time, 44 byte-identical across all
three, and the two that differ are the two the operator typed.

`CREATED` below is the `GGD` doing verbatim. The repo's own convention is to
inline measured bytes rather than build a plausible-looking dictionary -- a
fixture that agrees with the code is a fixture that proves nothing, and the
counter-example this module turns on (`palletBuildingConsolidateBy` beside
`displayedPalletBuildingConsolidateBy`) only exists because the real form has
both.
"""

from __future__ import annotations

import json
from dataclasses import replace

from sro.domain.execution.field_notes import keys_named
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.write_plan import (
    begins_again_at,
    demonstrated_writes,
    scaffolding_for,
    seen_values,
    wanted_by,
    write_plan_for,
)
from sro.domain.observation.gesture import Action, Body, Call, Gesture, Target
from sro.domain.shared.hosts import REDACTED
from sro.domain.skill.workflow import Step, Workflow

HOST = "https://bf56-kms-wms-web-np2.jdadelivers.com"
PATH = "/data/WM/wm/customerTypes"
LEDGER = (VerifiedWrite(method="POST", path_pattern=PATH),)

# The `GGD` body, exactly as it was sent.
CREATED: dict[str, object] = {
    "URNFormat": "",
    "absoluteGroup": "",
    "allocationSearchPath": "",
    "allowSourceFacilityOverridesFlag": False,
    "bulkPickingFlag": False,
    "carrierGroup": "",
    "createShipmentBy": "",
    "crossDockFlag": -1,
    "customerType": "GGD",
    "dateControlledInvFlag": False,
    "departmentNumber": "",
    "displayedPalletBuildingConsolidateBy": "Inherit from transport mode",
    "doubleWrapped": "",
    "earlyDeliveryThreshold": 0,
    "enforceEarlyDeliveryRuleFlag": False,
    "enforceLateDeliveryRuleFlag": False,
    "freshnessDateCode": "",
    "fullSingleItemCartonEncoding": "",
    "fullSingleItemPalletEncoding": "",
    "inventoryRotationMethod": "",
    "inventoryStatusProgression": "",
    "label4Sides": "",
    "lateDeliveryThreshold": 0,
    "loadAttribute5": "",
    "longDescription": "leaning new SRO type 01",
    "manufacturerId": "",
    "maxQuantityOvershipPercentage": 0,
    "maxQuantityUndershipPercentage": 0,
    "minimumShelfLife": 0,
    "mixedPartialCartonEncoding": "",
    "mixedPartialPalletEncoding": "",
    "outboundDateWindow": 0,
    "outboundDateWindowUnit": "MIN",
    "overshippingRule": "",
    "palletBuildingConsolidateBy": "",
    "quantityOvershipLimit": 0,
    "quantityUndershipLimit": 0,
    "requiredForTMSPlanning": "",
    "reservationPriority": "",
    "shipDateValidationTransitService": "",
    "shipLabel": "",
    "shipmentModificationRuleCode": "",
    "shotDescription": "",
    "slipSheet": "",
    "undershippingRule": "",
    "wrapped": "",
}

CODE = "customertype-customerType"
DESCRIPTION = "customertype-longDescription"


def _call(body: dict[str, object] | None, *, method: str = "POST", url: str = "") -> Call:
    # `ensure_ascii=False`, as the store holds it. Redaction runs in Python and
    # writes `«redacted»` into the text literally, so a fixture that escaped the
    # guillemets to `\\u00ab` would hide the marker from `unreplayable` and the
    # test would pass while the module did the wrong thing. Caught exactly that
    # way, writing the test below.
    text = None if body is None else json.dumps(body, ensure_ascii=False)
    return Call(
        method=method,
        url=url or f"{HOST}{PATH}?siteId=SG",
        started_at=1_000.0,
        request_body=None if text is None else Body(text=text, size_bytes=len(text)),
        status=201,
    )


def _answered(
    gesture_id: str, body: dict[str, object] | None, answer: dict[str, object]
) -> Gesture:
    """One doing of the save whose reply the recorder also kept.

    The real capture keeps response bodies -- 4 of the 4 writes in the
    extension's own `fixtures/batch-teaching.json` carry one -- and they are
    what says which slots the server hands back unchanged.
    """
    gesture = _saving(gesture_id, body)
    text = json.dumps(answer, ensure_ascii=False)
    gesture.requests[0] = replace(
        gesture.requests[0], response_body=Body(text=text, size_bytes=len(text))
    )
    return gesture


def _saving(gesture_id: str, body: dict[str, object] | None, **kw: str) -> Gesture:
    """One doing of the save: a click that produced the create."""
    return Gesture(
        id=gesture_id,
        tenant="greyorange",
        stream_id="str-1",
        batch_id="bat-1",
        at=1_000.0,
        url=f"{HOST}/portal?siteId=SG",
        system=HOST,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1_000.0, target=Target(tag="button", name="Save")),
        requests=[_call(body, **kw)],
    )


def _step(*cites: str) -> Step:
    return Step(order=6, says="Click the Save button", system=HOST, cites=list(cites))


def _twice(
    first: dict[str, object] | None = None, second: dict[str, object] | None = None
) -> dict[str, Gesture]:
    """The job as it is actually stored: one step citing both doings."""
    a = first if first is not None else CREATED
    b = (
        second
        if second is not None
        else {**CREATED, "customerType": "GKB", "longDescription": "GKB type"}
    )
    return {"g1": _saving("g1", a), "g2": _saving("g2", b)}


# What the stored job says these two have been given. `DESCRIBED` is read off
# the fixture rather than retyped, so the two cannot drift apart.
DESCRIBED = str(CREATED["longDescription"])
SEEN: dict[str, frozenset[str]] = {
    CODE: frozenset({"GGD", "GKB"}),
    DESCRIPTION: frozenset({DESCRIBED, "GKB type"}),
}


# -- the two fields the job varies ---------------------------------------------


def test_the_two_fields_the_job_varies_are_the_two_this_run_fills() -> None:
    """The test that would have caught the defect this module exists for.

    46 keys in, 46 keys out, the operator's two values in the two slots, and the
    other 44 byte-identical to what the form sent.
    """
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", DESCRIPTION: "leaning new SRO type 006"},
        LEDGER,
        SEEN,
    )

    assert plan is not None
    sent = json.loads(plan.body or "{}")
    assert len(sent) == 46
    assert sent["customerType"] == "GPDP"
    assert sent["longDescription"] == "leaning new SRO type 006"
    assert {key: value for key, value in sent.items() if key not in plan.filled} == {
        key: value for key, value in CREATED.items() if key not in plan.filled
    }
    assert plan.filled == {"customerType": CODE, "longDescription": DESCRIPTION}


def test_the_twenty_eight_empty_fields_go_out_exactly_as_the_form_sent_them() -> None:
    """No `absent_as` anywhere near this path. An empty string is what the form
    sends for a box nobody touched, and `typed_values` drops empties so no
    `seen_values` can ever claim one."""
    plan = write_plan_for(_step("g1", "g2"), _twice(), {CODE: "GPDP"}, LEDGER, {CODE: SEEN[CODE]})

    assert plan is not None
    sent = json.loads(plan.body or "{}")
    assert sum(1 for value in sent.values() if value == "") == 28


def test_a_number_and_a_boolean_are_never_slots() -> None:
    """`crossDockFlag: -1` and the four other numbers, and the five booleans.
    A run's values are strings; a non-string field never binds, and the
    unaccounted rule refuses rather than coercing."""
    plan = write_plan_for(_step("g1", "g2"), _twice(), {CODE: "GPDP"}, LEDGER, {CODE: SEEN[CODE]})

    assert plan is not None
    sent = json.loads(plan.body or "{}")
    assert sent["crossDockFlag"] == -1
    assert sent["bulkPickingFlag"] is False
    assert sum(1 for value in sent.values() if isinstance(value, bool)) == 5


# -- what it refuses, and why each refusal is not a guess -----------------------


def test_a_display_twin_is_not_bound_by_its_name() -> None:
    """The counter-example that rules out a suffix join, and it is in the real
    body: `palletBuildingConsolidateBy` is the code the API stores (empty here)
    and `displayedPalletBuildingConsolidateBy` is the label it ignores. A
    control named `…ConsolidateBy` matches both. Nothing here binds by name, so
    neither is touched -- and a parameter claiming one refuses the plan rather
    than picking."""
    assert CREATED["palletBuildingConsolidateBy"] == ""
    assert CREATED["displayedPalletBuildingConsolidateBy"] == "Inherit from transport mode"

    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {"customertype-palletBuildingConsolidateBy": "Order"},
        LEDGER,
        {"customertype-palletBuildingConsolidateBy": frozenset({"Order"})},
    )

    assert plan is None, "a value nothing carries must never land in a lookalike key"


def test_a_value_the_form_transformed_refuses_the_whole_plan() -> None:
    """The ledger's own gotcha, and the reason the unaccounted rule exists:
    `csttyp truncates at 4 chars`. `knowledge-base/http/flows/lifecycle-
    customerTypes.json` records a harness asking for `ZV9680` and the body
    going out as `ZV96`.

    The typed value is not in the body, so nothing binds. Keeping the
    demonstration's value instead would create the demonstration's record and
    answer 201 while doing it."""
    asked, applied = "ZV9680", "ZV96"
    doings = _twice(
        {**CREATED, "customerType": applied},
        {**CREATED, "customerType": "GKB", "longDescription": "GKB type"},
    )

    plan = write_plan_for(
        _step("g1", "g2"), doings, {CODE: asked}, LEDGER, {CODE: frozenset({asked, "GKB"})}
    )

    assert plan is None


def test_a_parameter_this_run_supplied_that_the_body_does_not_carry_refuses() -> None:
    """The general form. Anything the operator was asked for must have somewhere
    to go, or the call sends the demonstration's value in its place."""
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", "customertype-nowhere": "x"},
        LEDGER,
        {**SEEN, "customertype-nowhere": frozenset({"x"})},
    )

    assert plan is None


def test_two_parameters_that_disagree_about_one_slot_refuse_the_plan() -> None:
    """A constant of the job that happens to equal some parameter's value turns
    into a slot the runner would substitute. Where two parameters claim one
    slot and say DIFFERENT things, there is no way to tell which the operator
    meant, and a warehouse record is the wrong place to guess."""
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", "other": "SOMETHING ELSE"},
        LEDGER,
        {CODE: SEEN[CODE], "other": SEEN[CODE]},
    )

    assert plan is None


def test_two_names_for_one_value_is_not_ambiguity() -> None:
    """The rule above used to refuse on the COUNT of claimants, and that broke
    the one job this deployment runs.

    Mining named the same value twice -- `Customer Type`, the label an operator
    reads, and `customertype-customerType`, the key the form posts -- so both
    claim the one slot. Refusing on the count made the write unreplayable for
    every run that supplied them, which is every run the gather fills, because
    it answers for each parameter the job declares. Measured on the deployment
    2026-09-16: the replay was refused, the ladder fell to a model, and the
    model pressed Save on a form that run had never filled.

    Two names for one value is not ambiguity. Two values for one slot is, and
    the test above still holds it.
    """
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", "other": "GPDP"},
        LEDGER,
        {CODE: SEEN[CODE], "other": SEEN[CODE]},
    )

    assert plan is not None
    assert '"GPDP"' in plan.body


def test_one_demonstration_names_no_parameters_and_so_replays_nothing() -> None:
    """Tied to the evidence rather than to a constant of its own: with one doing
    nothing distinguishes a slot from a constant."""
    once = {"g1": _saving("g1", CREATED)}

    assert write_plan_for(_step("g1"), once, {CODE: "GPDP"}, LEDGER, SEEN) is None


def test_a_body_this_run_changes_nothing_in_gets_no_plan_at_all() -> None:
    """A job with no parameters replays byte for byte, and a plan cannot do
    that -- so the honest answer is to decline and let the recorded bytes go.

    This test used to assert the opposite, and it passed, and it was wrong
    twice. `json.loads(plan.body) == CREATED` compares DOCUMENTS, so it agreed
    while the plan re-serialised `{"a":1}` into `{"a": 1}` -- different bytes,
    for nothing, and wrong outright for a body anything signs. And a plan sets
    `rewrote`, which `verify` reads as "the status no longer proves the
    demonstrated effect": a job nobody parameterised would have started
    demanding a read-back to confirm a body nobody rewrote.
    """
    assert write_plan_for(_step("g1", "g2"), _twice(), {}, LEDGER, {}) is None


def test_an_endpoint_the_ledger_has_not_watched_succeed_gets_no_plan() -> None:
    """Membership, not resemblance. `/customerTypes` and `/customers` are one
    character apart in a list of eighty write targets."""
    elsewhere = (VerifiedWrite(method="POST", path_pattern="/data/WM/wm/customers"),)

    assert write_plan_for(_step("g1", "g2"), _twice(), {CODE: "GPDP"}, elsewhere, SEEN) is None


def test_a_body_with_a_struck_out_credential_is_never_aimed() -> None:
    """`unreplayable` first. A body the redactor went through carries the marker
    where a value was, and substituting into it would post the marker's text."""
    struck = _twice()
    struck["g1"] = replace(
        struck["g1"],
        requests=[_call({**CREATED, "token": REDACTED})],
    )

    assert write_plan_for(_step("g1", "g2"), struck, {CODE: "GPDP"}, LEDGER, SEEN) is None


def test_a_form_encoded_body_is_not_a_body_this_can_aim() -> None:
    """Replayable byte for byte, and this module has nothing to add to it."""
    legacy = _twice()
    for key in legacy:
        legacy[key] = replace(
            legacy[key],
            requests=[
                Call(
                    method="POST",
                    url=f"{HOST}{PATH}",
                    started_at=1_000.0,
                    request_body=Body(text="customerType=GGD&longDescription=x", size_bytes=33),
                    status=201,
                )
            ],
        )

    assert write_plan_for(_step("g1", "g2"), legacy, {CODE: "GPDP"}, LEDGER, SEEN) is None


def test_a_read_is_never_a_write_plan() -> None:
    reads = _twice()
    for key in reads:
        reads[key] = replace(reads[key], requests=[_call(CREATED, method="GET")])

    assert write_plan_for(_step("g1", "g2"), reads, {CODE: "GPDP"}, LEDGER, SEEN) is None


# -- the steps the replayed call makes unnecessary ------------------------------


def _typing(gesture_id: str, order: int) -> Gesture:
    """A step that types into the form and calls nothing. Measured: steps 4 and
    5 of the real job make no network call at all."""
    return Gesture(
        id=gesture_id,
        tenant="greyorange",
        stream_id="str-1",
        batch_id="bat-1",
        at=float(order),
        url=f"{HOST}/portal?siteId=SG",
        system=HOST,
        tab_id=1,
        frame_url=None,
        action=Action(kind="type", at=float(order), value="x"),
        requests=[],
    )


def _job(*steps: Step) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant="greyorange",
        title="Create a Customer Type",
        narrative="n",
        systems=[HOST],
        steps=list(steps),
    )


def test_the_steps_that_only_put_the_form_on_screen_are_not_needed() -> None:
    """The measured shape of the real job: six steps, one write. Steps 2 to 5
    exist to make the form appear, and a replayed call does not need them."""
    by_id = {
        **{f"t{n}": _typing(f"t{n}", n) for n in (2, 3, 4, 5)},
        "g1": _saving("g1", CREATED),
    }
    job = _job(
        *(Step(order=n, says=f"step {n}", system=HOST, cites=[f"t{n}"]) for n in (2, 3, 4, 5)),
        _step("g1"),
    )

    assert scaffolding_for(job, by_id, write_step=6) == (2, 3, 4, 5)


def test_a_step_before_an_earlier_write_belongs_to_that_write_and_not_this_one() -> None:
    """The partition that makes this right for a job with two writes in it. A
    field typed at step 2 whose value leaves in a call at step 3 feeds step 3,
    so collapsing it into step 6's replay would drop it."""
    by_id = {
        "t2": _typing("t2", 2),
        "w3": _saving("w3", CREATED),
        "t4": _typing("t4", 4),
        "g1": _saving("g1", CREATED),
    }
    job = _job(
        Step(order=2, says="type", system=HOST, cites=["t2"]),
        Step(order=3, says="an earlier write", system=HOST, cites=["w3"]),
        Step(order=4, says="type", system=HOST, cites=["t4"]),
        _step("g1"),
    )

    assert scaffolding_for(job, by_id, write_step=6) == (4,)


def test_nothing_after_the_write_is_scaffolding() -> None:
    by_id = {"g1": _saving("g1", CREATED), "t7": _typing("t7", 7)}
    job = _job(_step("g1"), Step(order=7, says="after", system=HOST, cites=["t7"]))

    assert scaffolding_for(job, by_id, write_step=6) == ()


def test_a_step_that_types_a_password_is_never_scaffolding() -> None:
    """Its value was struck out of the evidence, so no replayed body can be
    carrying it and skipping the step would skip the password."""
    secret = _typing("t2", 2)
    secret = replace(
        secret,
        action=replace(
            secret.action, target=Target(tag="input", name="password", secret=True), value=None
        ),
    )
    by_id = {"t2": secret, "g1": _saving("g1", CREATED)}
    job = _job(Step(order=2, says="type the password", system=HOST, cites=["t2"]), _step("g1"))

    assert scaffolding_for(job, by_id, write_step=6) == ()


# -- what a stored job says its parameters have been given ----------------------


def test_the_values_a_parameter_has_been_seen_taking_come_off_the_stored_job() -> None:
    job = _job(_step("g1"))
    job.parameters = [
        {"name": CODE, "seen_values": ["GGD", "GKB"]},
        {"name": DESCRIPTION, "seen_values": ["one", "two"]},
    ]

    assert seen_values(job) == {
        CODE: frozenset({"GGD", "GKB"}),
        DESCRIPTION: frozenset({"one", "two"}),
    }


def test_a_parameter_the_model_named_badly_is_left_out_rather_than_half_read() -> None:
    """`workflow.parameters` is the mining pass's own model output and the
    schema is advisory, so every field here is checked rather than trusted. A
    blank value cannot be a slot either -- `typed_values` drops empties, so one
    appearing here came from somewhere that is not a typed value."""
    job = _job(_step("g1"))
    job.parameters = [
        {"name": "", "seen_values": ["x"]},
        {"name": CODE, "seen_values": "GGD"},
        {"seen_values": ["x"]},
        {"name": "blanks", "seen_values": ["  ", ""]},
        {"name": "kept", "seen_values": ["real", 7]},
    ]

    assert seen_values(job) == {"kept": frozenset({"real"})}


def test_the_fixture_encodes_a_body_the_way_the_store_holds_one() -> None:
    """The self-consistent trap, pinned.

    This file builds its bodies with its own encoder, so a fixture that encoded
    differently from the store would let every test above pass while proving
    nothing about real bytes. That is exactly what happened while writing it:
    `json.dumps` escapes `«redacted»` to `\\u00ab redacted \\u00bb`, so
    `unreplayable` could not see the marker and the struck-out-credential test
    was green against a body no store has ever held.

    The authoritative form was read back off the deployment on 2026-09-16 --
    redaction runs in Python and the marker lands in JSONB verbatim, so a stored
    body carries the guillemets themselves. This asserts the encoder this file
    uses agrees with that, once, where the other tests only assume it.
    """
    text = _call({"token": REDACTED}).request_body
    assert text is not None and text.text is not None

    assert REDACTED in text.text, "the fixture escaped the marker the store holds literally"
    assert "\\u00ab" not in text.text


# -- the edges a sweep found nothing standing on -------------------------------


def test_a_step_that_cites_nothing_has_no_call_to_aim() -> None:
    assert write_plan_for(_step(), {}, {CODE: "GPDP"}, LEDGER, SEEN) is None


def test_the_plan_carries_the_method_and_url_the_evidence_recorded() -> None:
    plan = write_plan_for(_step("g1", "g2"), _twice(), {CODE: "GPDP"}, LEDGER, {CODE: SEEN[CODE]})

    assert plan is not None
    assert plan.method == "POST"
    assert plan.url == f"{HOST}{PATH}?siteId=SG"
    assert plan.entry.path_pattern == PATH


def test_another_endpoint_on_the_same_host_is_not_this_step_s_write() -> None:
    """`_same_endpoint` compares the path as well as the origin. The warehouse
    posts to eighty different paths on one host, and two of them differ by a
    single word -- `/customerTypes` and `/customers`."""
    mixed = _twice()
    mixed["g2"] = replace(
        mixed["g2"],
        requests=[
            _call(
                {**CREATED, "customerType": "GKB"},
                url=f"{HOST}/data/WM/wm/customers?siteId=SG",
            )
        ],
    )

    # One body left to diff, so nothing is a slot and the supplied value has
    # nowhere to go.
    assert write_plan_for(_step("g1", "g2"), mixed, {CODE: "GPDP"}, LEDGER, SEEN) is None


def test_a_key_one_doing_carried_and_the_other_did_not_is_never_a_slot() -> None:
    """A form that changed between two recordings is not a value somebody typed,
    and substituting into it would send a field the demonstration never proved.
    So the diff runs over the keys both bodies have."""
    widened = dict(CREATED)
    widened["customerType"] = "GKB"
    widened["longDescription"] = "GKB type"
    widened["fieldAddedLater"] = "new"
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(CREATED, widened),
        {CODE: "GPDP"},
        LEDGER,
        {CODE: SEEN[CODE]},
    )

    assert plan is not None
    sent = json.loads(plan.body or "{}")
    assert "fieldAddedLater" not in sent, "a key only one doing carried became a slot"
    assert len(sent) == 46


def test_a_constant_that_happens_to_equal_a_typed_value_is_still_a_constant() -> None:
    """The trap: a constant of the job that happens to
    equal some parameter's value turns into a slot the runner substitutes. The
    diff is what stops it -- a key both doings sent identically is structure,
    whatever its value looks like."""
    twin = "GGD"
    first = {**CREATED, "manufacturerId": twin}
    second = {
        **CREATED,
        "customerType": "GKB",
        "longDescription": "GKB type",
        "manufacturerId": twin,
    }

    plan = write_plan_for(
        _step("g1", "g2"), _twice(first, second), {CODE: "GPDP"}, LEDGER, {CODE: SEEN[CODE]}
    )

    assert plan is not None
    sent = json.loads(plan.body or "{}")
    assert sent["customerType"] == "GPDP"
    assert sent["manufacturerId"] == twin, "a constant equal to a typed value was substituted"
    assert plan.filled == {"customerType": CODE}


# -- what a read can actually be checked against -------------------------------


def test_a_slot_the_server_rewrites_is_not_one_a_read_can_confirm() -> None:
    """The display twin, measured rather than guessed.

    Over the 94 recorded creates whose request and response are both JSON
    objects, 16 send a value that appears nowhere in the answer -- every one of
    them a `…Description` key where the form posts the CODE and the server
    stores the LABEL it resolves to. `allocationAssetGroupDescription` sent
    `ZV9054` and came back `Any Handling unit for pallet movement`.

    A read-back looking for `ZV9054` there finds nothing and calls a correct
    record failed, which stops the run and empties the job's register of
    verified effects. So the slot is filled and simply never asked about.
    """
    first = {**CREATED, "longDescription": "ZV9054"}
    second = {**CREATED, "customerType": "GKB", "longDescription": "ZV8811"}
    twice = {
        # Both doings answer, and both show the same thing: the code went into
        # `longDescription` and the label came back.
        "g1": _answered("g1", first, {**first, "longDescription": "Any handling unit"}),
        "g2": _answered("g2", second, {**second, "longDescription": "Inventory"}),
    }
    seen = {CODE: frozenset({"GGD", "GKB"}), DESCRIPTION: frozenset({"ZV9054", "ZV8811"})}

    plan = write_plan_for(
        _step("g1", "g2"), twice, {CODE: "GPDP", DESCRIPTION: "ZV7000"}, LEDGER, seen
    )

    assert plan is not None
    assert plan.filled == {"customerType": CODE, "longDescription": DESCRIPTION}, "both were sent"
    assert json.loads(plan.body or "{}")["longDescription"] == "ZV7000", "and both went out"
    assert plan.confirm == {"customerType": "GPDP"}, "only the slot the server gives back"


def test_a_demonstration_that_never_answered_says_nothing_about_any_slot() -> None:
    """Absence of evidence about a slot is not evidence about the slot.

    A capture with no response body does not show the server rewriting
    anything, so every slot stays checkable -- which is no weaker than the
    whole-body search this replaced, and keeps the belt that catches the
    ledger's own `csttyp truncates at 4 chars`.
    """
    plan = write_plan_for(
        _step("g1", "g2"), _twice(), {CODE: "GPDP", DESCRIPTION: "new"}, LEDGER, SEEN
    )

    assert plan is not None
    assert plan.confirm == {"customerType": "GPDP", "longDescription": "new"}


def test_one_doing_that_echoed_a_slot_does_not_answer_for_one_that_rewrote_it() -> None:
    """`all`, not `any`. A server that resolves a code only when it recognises
    it rewrites the slot sometimes, and a slot rewritten sometimes is one no
    read can be checked against."""
    first = {**CREATED, "longDescription": "ZV9054"}
    second = {**CREATED, "customerType": "GKB", "longDescription": "ZV8811"}
    twice = {
        "g1": _answered("g1", first, first),
        "g2": _answered("g2", second, {**second, "longDescription": "Inventory"}),
    }
    seen = {CODE: frozenset({"GGD", "GKB"}), DESCRIPTION: frozenset({"ZV9054", "ZV8811"})}

    plan = write_plan_for(
        _step("g1", "g2"), twice, {CODE: "GPDP", DESCRIPTION: "ZV7000"}, LEDGER, seen
    )

    assert plan is not None and plan.confirm == {"customerType": "GPDP"}


def _with_calls(gesture_id: str, *calls: Call) -> Gesture:
    """One doing whose whole recorded traffic is given, in order."""
    gesture = _saving(gesture_id, CREATED)
    gesture.requests[:] = list(calls)
    return gesture


def _answering(body: dict[str, object], answer: dict[str, object]) -> Call:
    """The create, with the reply the warehouse actually sends: the record
    inside `{"@type": "ResponseBodyWrapper", "data": {…}}`, which is the shape
    112 of the 114 successful writes in the recorded exchanges carry."""
    text = json.dumps({"@type": "ResponseBodyWrapper", "data": answer}, ensure_ascii=False)
    return replace(_call(body), response_body=Body(text=text, size_bytes=len(text)))


def test_the_answer_is_read_through_its_envelope_like_every_other_reader() -> None:
    """Read at the top level a Blue Yonder reply has `@type` and `data` and
    none of the record's own fields, so every slot would look rewritten and
    nothing would ever be confirmed -- on the one shape that is production."""
    first = {**CREATED, "longDescription": "ZV9054"}
    second = {**CREATED, "customerType": "GKB", "longDescription": "ZV8811"}
    twice = {
        "g1": _with_calls("g1", _answering(first, {**first, "longDescription": "A handling unit"})),
        "g2": _with_calls("g2", _answering(second, {**second, "longDescription": "Inventory"})),
    }
    seen = {CODE: frozenset({"GGD", "GKB"}), DESCRIPTION: frozenset({"ZV9054", "ZV8811"})}

    plan = write_plan_for(
        _step("g1", "g2"), twice, {CODE: "GPDP", DESCRIPTION: "ZV7000"}, LEDGER, seen
    )

    assert plan is not None
    assert plan.confirm == {"customerType": "GPDP"}, "the envelope hid the record"


def test_a_call_that_is_not_the_write_does_not_stop_the_search_for_one() -> None:
    """Every doing of a real step carries other traffic -- the screen loading,
    a beacon, the read that follows the write. The create is not the first
    call, and stopping at the first thing that is not it finds nothing.
    """
    first = {**CREATED, "longDescription": "ZV9054"}
    second = {**CREATED, "customerType": "GKB", "longDescription": "ZV8811"}
    noise = _call(None, method="GET", url=f"{HOST}/portal/menu")
    quiet = replace(_call(first), response_body=None)
    twice = {
        # A gesture the step cites and the store does not have comes first, so
        # a search that gave up on the first miss would never reach either
        # doing. Then a call to another path, then the create with no reply
        # kept, then the create that answered.
        "g1": _with_calls(
            "g1", noise, quiet, _answering(first, {**first, "longDescription": "A handling unit"})
        ),
        # `g2` echoes BOTH slots, so the narrowing can only come from `g1` --
        # and it only comes from `g1` if the search got past the call to
        # another path and the doing whose reply was never kept.
        "g2": _with_calls("g2", noise, _answering(second, second)),
    }
    seen = {CODE: frozenset({"GGD", "GKB"}), DESCRIPTION: frozenset({"ZV9054", "ZV8811"})}

    plan = write_plan_for(
        _step("gone", "g1", "g2"), twice, {CODE: "GPDP", DESCRIPTION: "ZV7000"}, LEDGER, seen
    )

    assert plan is not None
    assert plan.confirm == {"customerType": "GPDP"}


def test_a_body_that_cannot_be_replayed_is_not_evidence_about_any_slot() -> None:
    """`unreplayable` is a refusal of its own, separate from "a different
    endpoint", and both have to skip. Reading a struck-out doing as evidence
    would compare the redaction marker against what the server stored and
    conclude the server rewrites a slot it hands straight back.
    """
    struck = {**CREATED, "customerType": "GZZ", "longDescription": REDACTED}
    first = {**CREATED, "longDescription": "kept as sent"}
    second = {**CREATED, "customerType": "GKB", "longDescription": "kept as sent too"}
    twice = {
        # The struck doing sits beside the clean one and answered with
        # something else in the slot, so a search that let it through would
        # drop `longDescription`. Second, because `recorded_call` takes the
        # step's write off the front and an unreplayable one there is refused
        # before any of this -- which is a different rule, already tested.
        "g1": _with_calls(
            "g1",
            _answering(first, first),
            _answering(struck, {**struck, "longDescription": "A handling unit"}),
        ),
        "g2": _with_calls("g2", _answering(second, second)),
    }
    seen = {
        CODE: frozenset({"GGD", "GKB"}),
        DESCRIPTION: frozenset({"kept as sent", "kept as sent too"}),
    }

    plan = write_plan_for(
        _step("g1", "g2"), twice, {CODE: "GPDP", DESCRIPTION: "new"}, LEDGER, seen
    )

    assert plan is not None
    assert plan.confirm == {"customerType": "GPDP", "longDescription": "new"}, (
        "a doing nothing may replay is not a doing that says what the server keeps"
    )


def test_a_call_says_which_parameters_its_body_carries_without_being_given_any() -> None:
    """`wanted_by` is asked BEFORE anybody knows what the run holds, which is
    the whole point of it.

    Every guard downstream asked "were we given values we could not place", and
    a run given nothing has none to fail to place -- so the one case where
    replaying a recording is most certainly wrong was the one case they let
    through. Measured on the deployment 2026-09-16: a run whose gather came
    back empty replayed the demonstration's own body.
    """
    # Both fields this job varies, named without a single value being supplied.
    assert wanted_by(_step("g1", "g2"), _twice(), SEEN) == frozenset({CODE, DESCRIPTION})
    # A call whose body carries no parameter at all still replays exactly as it
    # was demonstrated, which is what most calls are.
    assert wanted_by(_step("g1"), {"g1": _saving("g1", CREATED)}, SEEN) == frozenset()


def test_the_same_value_under_two_names_is_carried_rather_than_refused() -> None:
    """The rule this narrows exists for the transformed-value case: a value the
    operator supplied that no key carries means the body would go out with the
    demonstration's value in its place, silently, because the endpoint answers
    201 either way.

    A value that equals one already IN the body is not that. Measured on the
    deployment 2026-09-16: mining declared this job's two fields four times --
    `Customer Type`, the label an operator reads, beside
    `customertype-customerType`, the key the form posts -- and the gather
    answers for every parameter a job declares, so every gathered run arrived
    holding four values for two slots. Two were placed, two were the same
    strings under another name, and the plan refused: the ladder fell to a
    model, and the model pressed Save on a form that run had never filled.
    """
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", DESCRIPTION: DESCRIBED, "Customer Type": "GPDP"},
        LEDGER,
        SEEN,
    )

    assert plan is not None
    assert json.loads(plan.body)["customerType"] == "GPDP"


def test_a_different_value_with_nowhere_to_go_still_refuses() -> None:
    """The half of that rule which must not move. A value the body does not
    carry, and which is not something the body carries under another name, is
    the transformed case -- and sending the body without it sends the
    demonstration's value instead."""
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", DESCRIPTION: DESCRIBED, "site": "SG"},
        LEDGER,
        SEEN,
    )

    assert plan is None


# -- where a run that came up short has to start over ---------------------------


def test_a_resumed_run_goes_back_to_where_the_form_was_built() -> None:
    """Not to the step that stopped.

    That one re-types a field into whatever is on the screen a minute later,
    and the operator may well have navigated off the half-filled form by then:
    the step acts on a screen that is not the one it was recorded against.
    """
    by_id = {"t4": _typing("t4", 4), "t5": _typing("t5", 5)}
    job = _job(
        Step(order=2, says="open the screen", system=HOST, cites=[]),
        Step(order=3, says="press Add", system=HOST, cites=[]),
        Step(order=4, says="type the code", system=HOST, cites=["t4"]),
        Step(order=5, says="type the description", system=HOST, cites=["t5"]),
    )

    # Stopped typing the description: back to opening the screen, because
    # nothing between them wrote.
    assert begins_again_at(job, by_id, stopped_at=5) == 2


def test_a_resumed_run_never_starts_on_the_far_side_of_a_write() -> None:
    """The whole safety argument, and the same one `scaffolding_for` makes: a
    write that went out and may have landed is not a step to try again."""
    by_id = {"g1": _saving("g1", CREATED), "t7": _typing("t7", 7), "t8": _typing("t8", 8)}
    job = _job(
        Step(order=2, says="open the screen", system=HOST, cites=[]),
        _step("g1"),
        Step(order=7, says="press Add again", system=HOST, cites=["t7"]),
        Step(order=8, says="type the second code", system=HOST, cites=["t8"]),
    )

    # The save at step 6 is behind it, so the rebuild starts AFTER it -- never
    # at step 2, which would create the first record a second time.
    assert begins_again_at(job, by_id, stopped_at=8) == 7


def test_a_run_that_stopped_on_its_own_first_step_starts_there() -> None:
    """There is nothing before it to rebuild from."""
    job = _job(Step(order=2, says="open the screen", system=HOST, cites=[]))

    assert begins_again_at(job, {}, stopped_at=2) == 2


# -- a field nobody demonstrated, and what makes filling it safe ---------------

DECLARED = keys_named(["Department"], {"departmentNumber": {"labels": ["Department"]}})
"""The join `field_notes.keys_named` makes, which is what the runner hands in.
`_slots` never names `departmentNumber` -- both doings send it empty, so it
does not vary -- and the form posts it all the same, which is what makes it
fillable at all."""


def test_a_field_no_doing_varied_is_filled_from_the_declared_key() -> None:
    """The case this exists for.

    A job's slots are what two doings proved VARY, and the form posts 46 keys.
    So `Department: Inbound` is a reasonable request naming a slot this write
    already sends -- as the empty string the form sends for a box nobody
    touched -- and the value had nowhere to go.
    """
    plan = write_plan_for(
        _step("g1", "g2"),
        {
            "g1": _answered("g1", CREATED, {"customerType": "GGD", "departmentNumber": ""}),
            "g2": _answered(
                "g2",
                {**CREATED, "customerType": "GKB"},
                {"customerType": "GKB", "departmentNumber": ""},
            ),
        },
        {CODE: "GPDP", "Department": "Inbound"},
        LEDGER,
        {CODE: SEEN[CODE]},
        DECLARED,
    )

    assert plan is not None
    sent = json.loads(plan.body or "{}")
    assert sent["departmentNumber"] == "Inbound"
    # And it must prove it landed. Nothing demonstrated this slot, so a status
    # says nothing about it: the request went, and the field may have been
    # ignored, renamed or silently dropped.
    assert plan.confirm["departmentNumber"] == "Inbound"


def test_a_field_the_server_never_echoes_is_not_filled_at_all() -> None:
    """Item 5, and the reason item 4 is safe. A slot no later read can be
    checked against is a value written where nobody can confirm it -- which is
    the wrong record this whole ladder exists to prevent."""
    plan = write_plan_for(
        _step("g1", "g2"),
        {
            "g1": _answered("g1", CREATED, {"customerType": "GGD"}),
            "g2": _answered("g2", {**CREATED, "customerType": "GKB"}, {"customerType": "GKB"}),
        },
        {CODE: "GPDP", "Department": "Inbound"},
        LEDGER,
        {CODE: SEEN[CODE]},
        DECLARED,
    )

    assert plan is not None
    assert json.loads(plan.body or "{}")["departmentNumber"] == ""
    assert "departmentNumber" not in plan.confirm


def test_demonstrations_that_answered_nothing_fill_nothing_undemonstrated() -> None:
    """`None` is "no evidence about echoing", which is not evidence of
    echoing."""
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", "Department": "Inbound"},
        LEDGER,
        {CODE: SEEN[CODE]},
        DECLARED,
    )

    assert plan is not None
    assert json.loads(plan.body or "{}")["departmentNumber"] == ""


def test_a_declared_key_no_recorded_body_carries_is_not_added() -> None:
    """Adding a key no body ever sent is this system deciding what the endpoint
    accepts, from a dictionary that describes a screen."""
    plan = write_plan_for(
        _step("g1", "g2"),
        {
            "g1": _answered("g1", CREATED, {"customerType": "GGD", "invented": "x"}),
            "g2": _answered(
                "g2", {**CREATED, "customerType": "GKB"}, {"customerType": "GKB", "invented": "x"}
            ),
        },
        {CODE: "GPDP", "Nowhere": "Inbound"},
        LEDGER,
        {CODE: SEEN[CODE]},
        keys_named(["Nowhere"], {"invented": {"labels": ["Nowhere"]}}),
    )

    assert plan is not None
    assert "invented" not in json.loads(plan.body or "{}")


def test_the_evidence_wins_where_both_could_bind_one_slot() -> None:
    """`_assigned` decided from what the operator was seen typing, which is
    stronger than a declaration."""
    plan = write_plan_for(
        _step("g1", "g2"),
        {
            "g1": _answered("g1", CREATED, {"customerType": "GGD"}),
            "g2": _answered("g2", {**CREATED, "customerType": "GKB"}, {"customerType": "GKB"}),
        },
        {CODE: "GPDP", "Customer Type": "OTHER"},
        LEDGER,
        {CODE: SEEN[CODE]},
        keys_named(["Customer Type"], {"customerType": {"labels": ["Customer Type"]}}),
    )

    assert plan is not None
    assert json.loads(plan.body or "{}")["customerType"] == "GPDP"
    assert plan.filled["customerType"] == CODE


def test_a_slot_the_record_returns_but_never_echoed_is_still_fillable() -> None:
    """The difference between `_returned` and `_echoed`, measured.

    On this deployment's own create, 2026-09-19: 46 keys sent, 43 in the
    record, 15 echoed unchanged. The 28 that disagree are the boxes nobody
    touched -- sent as `""` and stored as `null` -- so an echo test excludes
    precisely the fields a request might name and a demonstration never
    filled, which is every field this exists for.

    Whether the server accepts THIS value is what the read-back answers, and
    fails the step on.
    """
    answer = {"customerType": "GGD", "departmentNumber": None}
    plan = write_plan_for(
        _step("g1", "g2"),
        {
            "g1": _answered("g1", CREATED, answer),
            "g2": _answered(
                "g2", {**CREATED, "customerType": "GKB"}, {**answer, "customerType": "GKB"}
            ),
        },
        {CODE: "GPDP", "Department": "Inbound"},
        LEDGER,
        {CODE: SEEN[CODE]},
        DECLARED,
    )

    assert plan is not None
    # Sent as "" by both doings and returned as null by both, so nothing
    # echoed it -- and the record plainly holds the key.
    assert json.loads(plan.body or "{}")["departmentNumber"] == "Inbound"
    assert plan.confirm["departmentNumber"] == "Inbound"


def test_a_slot_no_record_ever_held_is_not_filled() -> None:
    """A key the server never returns cannot be checked at all, and a value
    written where nobody can confirm it is the wrong record this ladder exists
    to prevent."""
    plan = write_plan_for(
        _step("g1", "g2"),
        {
            "g1": _answered("g1", CREATED, {"customerType": "GGD"}),
            "g2": _answered("g2", {**CREATED, "customerType": "GKB"}, {"customerType": "GKB"}),
        },
        {CODE: "GPDP", "Department": "Inbound"},
        LEDGER,
        {CODE: SEEN[CODE]},
        DECLARED,
    )

    assert plan is not None
    assert json.loads(plan.body or "{}")["departmentNumber"] == ""
    assert "departmentNumber" not in plan.confirm


def test_one_doing_that_returned_a_key_is_not_enough() -> None:
    """`all`, not `any`: one doing that returned a key proves nothing if
    another did not."""
    plan = write_plan_for(
        _step("g1", "g2"),
        {
            "g1": _answered("g1", CREATED, {"customerType": "GGD", "departmentNumber": None}),
            "g2": _answered("g2", {**CREATED, "customerType": "GKB"}, {"customerType": "GKB"}),
        },
        {CODE: "GPDP", "Department": "Inbound"},
        LEDGER,
        {CODE: SEEN[CODE]},
        DECLARED,
    )

    assert plan is not None
    assert json.loads(plan.body or "{}")["departmentNumber"] == ""


# --- a write whose value is in its path ---------------------------------------

DELETED = VerifiedWrite(method="DELETE", path_pattern=f"{PATH}/{{id}}")


def _deleting(gesture_id: str, code: str, *, status: int = 200) -> Gesture:
    """One doing of the delete, as the deployment recorded six of them: the OK
    click, and `DELETE .../customerTypes/<code>?siteId=SG` answered 200."""
    gesture = _saving(gesture_id, None, method="DELETE", url=f"{HOST}{PATH}/{code}?siteId=SG")
    gesture.requests[0] = replace(gesture.requests[0], status=status)
    return gesture


def _deletes(*codes: str) -> dict[str, Gesture]:
    return {f"d{n}": _deleting(f"d{n}", code) for n, code in enumerate(codes)}


SEEN_CODES = {"Customer Type": frozenset({"MRN5", "DDLS", "ZQ46", "GPP"})}


def test_a_delete_is_aimed_at_the_record_this_run_names() -> None:
    """Measured on the deployment 2026-09-22: six recorded `DELETE`s, every one
    answered 200, and every last segment a code the operator typed into the
    job's one parameter. The recording's url names the demonstration's record;
    replayed as it stands it deletes MRN5 when the run asked for MRN1."""
    by_id = _deletes("MRN5", "DDLS")
    plan = write_plan_for(
        Step(order=4, says="Confirm the deletion", system=HOST, cites=list(by_id)),
        by_id,
        {"Customer Type": "MRN1"},
        (DELETED,),
        SEEN_CODES,
    )

    assert plan is not None
    assert plan.url == f"{HOST}{PATH}/MRN1?siteId=SG"
    assert plan.method == "DELETE" and plan.body is None
    # Nothing a read could settle: the status of a url that names the record is
    # the answer, and `verify` holds on it.
    assert plan.confirm == {}


def test_one_doing_proves_nothing_about_which_segment_varies() -> None:
    by_id = _deletes("MRN5")
    step = Step(order=4, says="Confirm the deletion", system=HOST, cites=list(by_id))

    assert write_plan_for(step, by_id, {"Customer Type": "MRN1"}, (DELETED,), SEEN_CODES) is None


def test_a_demonstration_the_server_refused_proves_nothing() -> None:
    """A 404 demonstrated the wrong record, not the endpoint."""
    by_id = {"d0": _deleting("d0", "MRN5"), "d1": _deleting("d1", "DDLS", status=404)}
    step = Step(order=4, says="Confirm the deletion", system=HOST, cites=list(by_id))

    assert write_plan_for(step, by_id, {"Customer Type": "MRN1"}, (DELETED,), SEEN_CODES) is None


def test_a_value_that_decodes_to_a_traversal_is_never_sent() -> None:
    by_id = _deletes("MRN5", "DDLS")
    step = Step(order=4, says="Confirm the deletion", system=HOST, cites=list(by_id))

    assert write_plan_for(step, by_id, {"Customer Type": "../x"}, (DELETED,), SEEN_CODES) is None


def test_the_value_a_delete_path_carries_is_one_the_run_must_have() -> None:
    """`wanted_by` is what refuses a run holding nothing, and it read bodies
    only -- so a run pressed with no value would replay `DELETE .../MRN5`."""
    by_id = _deletes("MRN5", "DDLS")
    step = Step(order=4, says="Confirm the deletion", system=HOST, cites=list(by_id))

    assert wanted_by(step, by_id, SEEN_CODES) == {"Customer Type"}


def test_a_job_proves_the_delete_its_own_doings_show() -> None:
    by_id = _deletes("MRN5", "DDLS", "ZQ46")
    job = replace(
        _job(Step(order=4, says="Confirm the deletion", system=HOST, cites=list(by_id))),
        parameters=[{"name": "Customer Type", "seen_values": ["MRN5", "DDLS", "ZQ46"]}],
    )

    assert demonstrated_writes(job, by_id) == (DELETED,)


def test_a_create_is_not_admitted_by_its_demonstrations() -> None:
    """Only the one shape the evidence makes airtight. A body-carrying write
    still earns its place in the ledger by a run of ours watching it."""
    by_id = _twice()
    job = replace(
        _job(_step("g1", "g2")),
        parameters=[{"name": "Customer Type", "seen_values": ["GGD", "GKB"]}],
    )

    assert demonstrated_writes(job, by_id) == ()
