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

from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.write_plan import (
    scaffolding_for,
    seen_values,
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


def test_one_value_two_parameters_could_claim_refuses_the_plan() -> None:
    """A constant of the job that happens to equal some parameter's value turns
    into a slot the runner would substitute. With one body there is no way to
    tell, so neither claims it."""
    plan = write_plan_for(
        _step("g1", "g2"),
        _twice(),
        {CODE: "GPDP", "other": "GPDP"},
        LEDGER,
        {CODE: SEEN[CODE], "other": SEEN[CODE]},
    )

    assert plan is None


def test_one_demonstration_names_no_parameters_and_so_replays_nothing() -> None:
    """Tied to the evidence rather than to a constant of its own: with one doing
    nothing distinguishes a slot from a constant."""
    once = {"g1": _saving("g1", CREATED)}

    assert write_plan_for(_step("g1"), once, {CODE: "GPDP"}, LEDGER, SEEN) is None


def test_a_body_this_run_changes_nothing_in_is_still_a_plan() -> None:
    """A job with no parameters at all replays byte for byte, which is what it
    has always done and what the majority of calls still are."""
    plan = write_plan_for(_step("g1", "g2"), _twice(), {}, LEDGER, {})

    assert plan is not None
    assert json.loads(plan.body or "{}") == CREATED
    assert plan.filled == {}


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
    """The trap `from_rig` warns about: a constant of the job that happens to
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
