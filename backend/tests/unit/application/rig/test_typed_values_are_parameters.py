"""Typed values are parameters by default, decided in code (M3, 2026-09-27).

The greyorange mining baseline found every step of "Create a Customer Type"
and named 0 of its 4 typed values: the model reads a typed value as fixed
text. Code now makes every typed value a parameter, except a credential, a
chore's, and a value every doing (two at least) typed identically.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from sro.application.execution.run_workflow import _under_every_name
from sro.application.observation.mine_lately import MineLately
from sro.application.observation.mining_pass import (
    K_BRING_IN_TRIES,
    MineResult,
    _folded,
    fill_in_passwords,
    learn_parameters,
    mine,
)
from sro.domain.execution.compiled import compile_job
from sro.domain.execution.planning import value_for
from sro.domain.observation.gesture import Action, Body, Call, Component, Gesture, Target
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.learned import K_PARAMETERS_RULE
from sro.domain.skill.signing_in import Logins
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.application.rig.test_mine_pass import APP, _sign_in_kit
from tests.unit.fakes import FakeAccountLocks, FakeAsker, FakeUnitOfWork
from tests.unit.scripts.test_migrate_vault_keys import _job as _signing_in_job
from tests.unit.scripts.test_migrate_vault_keys import _sign_in

TENANT = TenantId("acme")
WMS = "https://wms.example.com"
NOW = datetime(2025, 2, 11, 23, tzinfo=UTC)
USERNAME = "clerk.one"


def _gesture(
    gid: str,
    at: float,
    kind: str,
    *,
    label: str | None = None,
    value: str | None = None,
    secret: bool = False,
    required: bool | None = None,
    body: dict[str, str] | None = None,
    item_id: str | None = None,
) -> Gesture:
    requests = (
        []
        if body is None
        else [
            Call(
                method="POST",
                url=f"{WMS}/api/customer-types",
                status=201,
                started_at=at,
                request_body=Body(text=json.dumps(body), mime_type="application/json"),
            )
        ]
    )
    return Gesture(
        id=gid,
        tenant=TENANT.value,
        stream_id="str_ct",
        batch_id="bat_ct",
        at=at,
        url=f"{WMS}/customer-types",
        system=WMS,
        tab_id=1,
        frame_url=None,
        action=Action(
            kind=kind,
            at=at,
            value=value,
            secret=secret,
            target=Target(
                tag="input" if kind != "click" else "button",
                name=label,
                secret=secret,
                required=required,
                component=Component(field_label=label, item_id=item_id)
                if (label or item_id) and not secret
                else None,
            ),
        ),
        requests=requests,
    )


def _customer_type(n: str, at: float, code: str, says: str, bill_to: str) -> list[Gesture]:
    """One doing, eleven steps: four typed values, the operator's own username
    typed into the box the recorded sign-in calls "username", and a password
    confirmed."""
    return [
        _gesture(f"{n}00", at + 0, "click", label="Masters"),
        _gesture(f"{n}01", at + 1, "click", label="Customer Types"),
        _gesture(f"{n}02", at + 2, "click", label="New"),
        _gesture(f"{n}03", at + 3, "type", label="Customer Type", value=code, required=True),
        _gesture(f"{n}04", at + 4, "type", label="Description", value=says),
        _gesture(f"{n}05", at + 5, "type", label="Short Description", value=code[:2]),
        _gesture(f"{n}06", at + 6, "select", label="Bill To", value=bill_to),
        _gesture(f"{n}07", at + 7, "type", label="username", value=USERNAME),
        _gesture(f"{n}08", at + 8, "type", label="Confirm Password", secret=True),
        _gesture(f"{n}09", at + 9, "click", label="Save", body={"code": code, "billTo": bill_to}),
        _gesture(f"{n}10", at + 10, "click", label="Close"),
    ]


def _proposed(doing: list[Gesture]) -> dict[str, object]:
    return {
        "title": "Create a Customer Type",
        "narrative": "the operator created a customer type",
        "systems": [WMS],
        "steps": [
            {"order": n, "cites": [one.id], "says": f"step {n}", "system": WMS}
            for n, one in enumerate(doing)
        ],
        "parameters": [],
    }


async def _mine(uow: FakeUnitOfWork, *proposals: dict[str, object]) -> MineResult:
    asker = FakeAsker(Answer(data={"workflows": list(proposals)}, cost_usd=0.01))
    return await mine(
        uow, tenant_id=TENANT, asker=asker, locks=FakeAccountLocks(), now=NOW, cap_usd=100.0
    )


async def _with_a_recorded_sign_in(uow: FakeUnitOfWork) -> None:
    await uow.gestures.add_gestures(tuple(_sign_in("h", user=USERNAME).values()))
    await uow.workflows.save(replace(_signing_in_job("h", signs_in=True), signs_out=False))


def _named(job: Workflow) -> dict[str, list[object]]:
    return {str(one["name"]): list(one["seen_values"]) for one in job.parameters}  # type: ignore[call-overload]


async def _work(uow: FakeUnitOfWork) -> Workflow:
    [job] = [one for one in await uow.workflows.known(TENANT) if one.title != "h"]
    return job


async def test_a_customer_type_doing_that_typed_four_values_gives_four_parameters() -> None:
    uow = FakeUnitOfWork()
    await _with_a_recorded_sign_in(uow)
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(doing))

    result = await _mine(uow, _proposed(doing))

    job = await _work(uow)
    assert _named(job) == {
        "Customer Type": ["GT7"],
        "Description": ["Ground transport"],
        "Short Description": ["GT"],
        "Bill To": ["Bill-To Customer"],
    }, "named by their labels, and neither the username nor the password is one"
    assert result.learned_parameters == 4
    compiled = compile_job(job, {one.id: one for one in doing}, learned={}, ledger=(), broken=())
    assert "unbound_parameter" not in [one.code for one in compiled.reasons], compiled.reasons


async def test_a_sign_in_job_gets_no_parameters() -> None:
    uow = FakeUnitOfWork()
    typed, _, left_for, login = _sign_in_kit()
    await uow.gestures.add_gestures(
        (typed("user", 10.0), typed("pw", 11.0, secret=True), left_for("go", 12.0, APP))
    )

    await _mine(uow, login("Log in", "user", "pw"))

    [job] = await uow.workflows.known(TENANT)
    assert job.signs_in is True
    assert job.parameters == [], "the username it typed is not asked for"


async def test_a_chore_gets_no_parameters_even_for_a_box_that_is_not_its_login() -> None:
    """A sign-in that also asks which company: that box is no credential, and
    still nobody is asked for it -- a chore is the broker's, not a job."""
    uow = FakeUnitOfWork()
    signing = _sign_in("h", user=USERNAME)
    company = replace(
        signing["h-user"],
        id="h-company",
        at=0.5,
        action=replace(
            signing["h-user"].action,
            at=0.5,
            value="GREYORANGE",
            target=Target(tag="input", name="Company"),
        ),
    )
    await uow.gestures.add_gestures((*signing.values(), company))
    job = replace(_signing_in_job("h", signs_in=True), signs_out=False)
    job.steps.insert(0, Step(order=-1, says="company", system=None, cites=["h-company"]))
    await uow.workflows.save(job)

    await _swept(uow)

    assert (await uow.workflows.get(TENANT, "wfl_h")).parameters == []
    assert uow.workflows.rules["wfl_h"] == K_PARAMETERS_RULE


async def test_a_value_two_doings_typed_identically_stays_fixed_and_one_that_differs_not() -> None:
    """A job stored before the rule, recognised again: Bill To was the same
    both times, the Customer Type was not."""
    uow = FakeUnitOfWork()
    first = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(first))
    await uow.workflows.save(_stored(first))
    again = _customer_type("ct_b_", 90_000.0, "RL2", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(again))

    await _mine(uow, _proposed(again))

    job = await _work(uow)
    assert _named(job) == {"Customer Type": ["GT7", "RL2"], "Short Description": ["GT", "RL"]}


def _doing(n: str, at: float, *typed: tuple[str, str]) -> list[Gesture]:
    """One doing that types each (label, value) and saves."""
    return [
        *(
            _gesture(f"{n}{k:02}", at + k, "type", label=label, value=value)
            for k, (label, value) in enumerate(typed)
        ),
        _gesture(f"{n}99", at + 99, "click", label="Save"),
    ]


def _proposed_one(doing: list[Gesture], title: str = "Move stock") -> dict[str, object]:
    return {**_proposed(doing), "title": title}


async def test_a_parameter_survives_a_later_doing_that_typed_its_first_value_again() -> None:
    """Mined from one doing with Warehouse=WH1, run with WH2 to WH5 (runs write
    no seen_values), then done by hand once more with WH1: the parameter the
    operator relies on is never taken back, or the next run would type WH1
    whatever its request asked."""
    uow = FakeUnitOfWork()
    first = _doing("wh_a_", 5000.0, ("Warehouse", "WH1"), ("SKU", "A-1"))
    await uow.gestures.add_gestures(tuple(first))
    await _mine(uow, _proposed_one(first))
    assert _named(await _work(uow)) == {"Warehouse": ["WH1"], "SKU": ["A-1"]}
    again = _doing("wh_b_", 90_000.0, ("Warehouse", "WH1"), ("SKU", "B-2"))
    await uow.gestures.add_gestures(tuple(again))

    await _mine(uow, _proposed_one(again))

    assert _named(await _work(uow)) == {"Warehouse": ["WH1"], "SKU": ["A-1", "B-2"]}


async def test_two_fields_typed_with_one_value_are_two_parameters_each_with_its_answer() -> None:
    uow = FakeUnitOfWork()
    doing = _doing("qp_a_", 5000.0, ("Quantity", "1"), ("Priority", "1"), ("SKU", "A-9"))
    await uow.gestures.add_gestures(tuple(doing))

    await _mine(uow, _proposed_one(doing))

    job = await _work(uow)
    assert _named(job) == {"Quantity": ["1"], "Priority": ["1"], "SKU": ["A-9"]}
    values = _under_every_name(job, {"Quantity": "5", "Priority": "2", "SKU": "Z-1"})
    by_id = {one.id: one for one in doing}
    typed = {
        by_id[step.cites[0]].action.target.name: value_for(step, by_id[step.cites[0]], values, None)
        for step in job.steps
        if by_id[step.cites[0]].action.kind == "type"
    }
    assert typed == {"Quantity": "5", "Priority": "2", "SKU": "Z-1"}


def _typed_into(job: Workflow, doing: list[Gesture], answers: dict[str, str]) -> dict[str, str]:
    values = _under_every_name(job, answers)
    by_id = {one.id: one for one in doing}
    return {
        str(by_id[step.cites[0]].action.target.name): str(
            value_for(step, by_id[step.cites[0]], values, None)
        )
        for step in job.steps
        if by_id[step.cites[0]].action.kind == "type"
    }


@pytest.mark.parametrize("model", ["Code", "Customer Code"])
async def test_a_parameter_the_model_proposed_is_tied_to_its_step_before_any_value(
    model: str,
) -> None:
    """QA: Code = Description, "Y"/"Y". The model proposes {name, seen_values}
    only, under the label or a word of its own, and Description is typed first:
    the model's parameter is tied to the step that lists it, so Description is
    never taken for it by value."""
    uow = FakeUnitOfWork()
    doing = _doing("cd_a_", 5000.0, ("Description", "Y"), ("Code", "Y"))
    await uow.gestures.add_gestures(tuple(doing))
    proposal = {**_proposed_one(doing), "parameters": [{"name": model, "seen_values": ["Y"]}]}
    proposal["steps"][1]["parameters"] = [model]

    await _mine(uow, proposal)

    job = await _work(uow)
    assert _named(job) == {model: ["Y"], "Description": ["Y"]}
    answers = {model: "C-1", "Description": "D-1"}
    assert _typed_into(job, doing, answers) == {"Code": "C-1", "Description": "D-1"}


async def _learned(doing: list[Gesture], parameters: list[dict[str, object]]) -> Workflow:
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures(tuple(doing))
    await uow.workflows.save(_stored(doing, parameters=parameters))
    await learn_parameters(
        uow,
        tenant_id=TENANT,
        known_id="wfl_ct",
        doings=(),
        by_id={one.id: one for one in doing},
        intents={},
        logins=Logins(),
    )
    return await uow.workflows.get(TENANT, "wfl_ct")


async def test_an_untied_parameter_is_never_matched_by_a_value_two_fields_hold() -> None:
    """A stored parameter no step lists: two fields typed its value, so the
    value cannot say which one it is, and each field is its own parameter."""
    doing = _doing("un_a_", 5000.0, ("Description", "Y"), ("Code", "Y"))

    job = await _learned(doing, [{"name": "Flag", "seen_values": ["Y"]}])

    assert _named(job) == {"Flag": ["Y"], "Description": ["Y"], "Code": ["Y"]}
    answers = {"Flag": "F", "Code": "C-1", "Description": "D-1"}
    assert _typed_into(job, doing, answers) == {"Code": "C-1", "Description": "D-1"}


async def test_an_untied_parameter_is_matched_by_a_value_only_one_field_holds() -> None:
    doing = _doing("un_b_", 5000.0, ("Description", "Y"), ("Code", "Z"))

    job = await _learned(doing, [{"name": "Flag", "seen_values": ["Y"]}])

    assert _named(job) == {"Flag": ["Y"], "Code": ["Z"]}
    assert _typed_into(job, doing, {"Flag": "F", "Code": "C-1"}) == {
        "Description": "F",
        "Code": "C-1",
    }


def test_an_untied_entry_is_folded_by_value_only_into_the_one_control_holding_it() -> None:
    untied: dict[str, object] = {"name": "Flag", "seen_values": ["Y"]}
    code: dict[str, object] = {"name": "Code", "names": ["Code"], "seen_values": ["Y"]}
    said: dict[str, object] = {
        "name": "Description",
        "names": ["Description"],
        "seen_values": ["Y"],
    }

    assert [one["name"] for one in _folded([dict(untied), dict(said), dict(code)])] == [
        "Flag",
        "Description",
        "Code",
    ]
    assert [one["name"] for one in _folded([dict(untied), dict(code)])] == ["Flag"]
    assert [one["name"] for one in _folded([dict(untied), {**untied, "name": "Other"}])] == [
        "Flag",
        "Other",
    ]


async def test_a_field_with_no_label_and_no_name_stays_fixed_text() -> None:
    """Named by its label, else its accessible name; never by the page's id for
    it or by the gesture's id. A required box with neither would otherwise be
    asked for as "ges_..." and make the job unrunnable."""
    uow = FakeUnitOfWork()
    doing = [
        _gesture("un_a_00", 5000.0, "type", value="Z-77", required=True),
        _gesture("un_a_01", 5001.0, "type", value="Q-12", item_id="combo-1034-inputEl"),
        _gesture("un_a_02", 5002.0, "type", label="Note", value="hello"),
        _gesture("un_a_99", 5099.0, "click", label="Save"),
    ]
    await uow.gestures.add_gestures(tuple(doing))

    await _mine(uow, _proposed_one(doing))

    job = await _work(uow)
    assert _named(job) == {"Note": ["hello"]}
    compiled = compile_job(job, {one.id: one for one in doing}, learned={}, ledger=(), broken=())
    assert "unbound_parameter" not in [one.code for one in compiled.reasons], compiled.reasons


def test_a_required_parameter_only_a_click_names_is_unbound() -> None:
    """A nav link named "Customer Type" fills nothing: only a control a step
    types into binds a parameter."""
    doing = [
        _gesture("nv_00", 1.0, "click", label="Customer Type"),
        _gesture("nv_01", 2.0, "type", label="Description", value="Rail"),
    ]
    job = replace(
        _stored(doing),
        parameters=[
            {"name": "Customer Type", "names": ["Customer Type"], "required": True},
            {"name": "Description", "names": ["Description"], "required": True},
        ],
    )

    compiled = compile_job(job, {one.id: one for one in doing}, learned={}, ledger=(), broken=())

    assert [one.detail for one in compiled.reasons if one.code == "unbound_parameter"] == [
        "Customer Type is required and no step fills it"
    ]


async def test_a_box_holding_the_username_is_input_unless_it_is_the_sign_ins_own_box() -> None:
    """A business box that happens to hold the operator's username ("Created
    By") is the operator's input; the box the recorded sign-in types its
    username into, on the system it signs in to, is a credential."""
    uow = FakeUnitOfWork()
    await _with_a_recorded_sign_in(uow)
    doing = _doing("cb_a_", 5000.0, ("Created By", USERNAME), ("username", USERNAME))
    await uow.gestures.add_gestures(tuple(doing))

    await _mine(uow, _proposed_one(doing))

    assert _named(await _work(uow)) == {"Created By": [USERNAME]}


async def test_a_healed_job_gets_the_rule_and_a_chore_keeps_what_it_had() -> None:
    uow = FakeUnitOfWork()
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(doing))
    await uow.workflows.save(_stored(doing, signs_in=None))
    await uow.gestures.add_gestures(tuple(_sign_in("h", user=USERNAME).values()))
    kept = [{"name": "Legacy", "names": ["Legacy"], "seen_values": ["x"]}]
    await uow.workflows.save(replace(_signing_in_job("h", signs_in=False), parameters=kept))

    assert await fill_in_passwords(uow, tenant_id=TENANT) == 2

    healed = await uow.workflows.get(TENANT, "wfl_ct")
    assert set(_named(healed)) == {"Customer Type", "Description", "Short Description", "Bill To"}
    chore = await uow.workflows.get(TENANT, "wfl_h")
    assert chore.signs_in is True and chore.parameters == kept


async def test_the_rule_is_stamped_only_once_every_placed_doing_was_read() -> None:
    """A pass reads the stored job and the doing it just recognised. A job with
    other doings placed on it has not had those read, so the sweep still owes
    it the rule; a new job has no other doing and is done."""
    uow = FakeUnitOfWork()
    first = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    older = _customer_type("ct_o_", 7000.0, "OL1", "Old", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(first + older))
    await uow.workflows.save(_stored(first))
    await uow.workflows.place(TENANT, "wfl_ct", tuple(one.id for one in older))
    again = _customer_type("ct_b_", 90_000.0, "RL2", "Rail", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(again))

    await _mine(uow, _proposed(again))

    assert "wfl_ct" not in uow.workflows.rules
    assert "RL2" in _named(await _work(uow))["Customer Type"]
    await _swept(uow)
    assert uow.workflows.rules["wfl_ct"] == K_PARAMETERS_RULE
    assert _named(await _work(uow))["Customer Type"] == ["GT7", "RL2", "OL1"]

    alone = FakeUnitOfWork()
    fresh = _doing("wh_a_", 5000.0, ("Warehouse", "WH1"))
    await alone.gestures.add_gestures(tuple(fresh))
    await _mine(alone, _proposed_one(fresh))
    assert alone.workflows.rules[(await _work(alone)).id] == K_PARAMETERS_RULE


async def test_a_parameter_a_step_names_or_that_was_ever_different_is_never_fixed() -> None:
    uow = FakeUnitOfWork()
    first = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(first))
    job = _stored(
        first,
        parameters=[
            {"name": "Bill To", "names": ["Bill To"], "seen_values": ["Bill-To Customer", "Other"]},
            {
                "name": "Description",
                "names": ["Description", "customertype-longDescription"],
                "seen_values": ["Ground transport"],
            },
        ],
    )
    job.steps[4].parameters = ["customertype-longDescription"]
    await uow.workflows.save(job)
    again = _customer_type("ct_b_", 90_000.0, "RL2", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(again))

    await _mine(uow, _proposed(again))

    named = _named(await _work(uow))
    assert named["Bill To"] == ["Bill-To Customer", "Other"], "it has been something else"
    assert named["Description"] == ["Ground transport"], "a step asks for it by a name it has"


def _stored(doing: list[Gesture], **over: object) -> Workflow:
    return replace(
        Workflow(
            id="wfl_ct",
            tenant=TENANT.value,
            title="Create a Customer Type",
            narrative="the operator created a customer type",
            systems=[WMS],
            steps=[
                Step(order=n, says=f"step {n}", system=WMS, cites=[one.id])
                for n, one in enumerate(doing)
            ],
            signs_in=False,
            signs_out=False,
        ),
        **over,
    )


def _sweeper(uow: FakeUnitOfWork, locks: FakeAccountLocks | None = None) -> MineLately:
    class _Nothing:
        async def execute(self, ctx: object) -> MineResult:
            return MineResult()

    class _NothingRead:
        async def execute(self, ctx: object) -> int:
            return 0

    return MineLately(uow, _Nothing(), _NothingRead(), locks or FakeAccountLocks(), window_hours=24)


async def _swept(uow: FakeUnitOfWork, locks: FakeAccountLocks | None = None) -> None:
    await _sweeper(uow, locks).execute(now=NOW)


async def test_the_sweep_brings_an_existing_job_in_once() -> None:
    uow = FakeUnitOfWork()
    await _with_a_recorded_sign_in(uow)
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(doing))
    await uow.workflows.save(_stored(doing))

    await _swept(uow)

    job = await uow.workflows.get(TENANT, "wfl_ct")
    assert set(_named(job)) == {"Customer Type", "Description", "Short Description", "Bill To"}
    assert uow.workflows.rules["wfl_ct"] == K_PARAMETERS_RULE
    assert uow.workflows.rules["wfl_h"] == K_PARAMETERS_RULE, "a chore is brought in too"
    assert (await uow.workflows.get(TENANT, "wfl_h")).parameters == [], "with nothing minted"

    await uow.workflows.save(replace(job, parameters=[]))
    await _swept(uow)

    assert (await uow.workflows.get(TENANT, "wfl_ct")).parameters == [], "once, not every sweep"


async def test_the_sweep_reads_the_doings_placed_on_a_job_and_keeps_a_constant_fixed() -> None:
    uow = FakeUnitOfWork()
    first = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    again = _customer_type("ct_b_", 90_000.0, "RL2", "Rail", "Bill-To Customer")
    third = _customer_type("ct_c_", 95_000.0, "SE1", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(first + again + third))
    await uow.workflows.save(_stored(first))
    await uow.workflows.place(TENANT, "wfl_ct", tuple(one.id for one in again + third))

    await _swept(uow)

    job = await uow.workflows.get(TENANT, "wfl_ct")
    assert _named(job) == {
        "Customer Type": ["GT7", "RL2", "SE1"],
        "Description": ["Ground transport", "Rail"],
        "Short Description": ["GT", "RL", "SE"],
    }, "Bill To was the same every time; the Description came back to its first value"


async def test_a_truly_constant_value_still_shows_the_fixed_values_warning() -> None:
    uow = FakeUnitOfWork()
    first = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    again = _customer_type("ct_b_", 90_000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(first + again))
    await uow.workflows.save(_stored(first))
    await uow.workflows.place(TENANT, "wfl_ct", tuple(one.id for one in again))

    await _swept(uow)

    job = await uow.workflows.get(TENANT, "wfl_ct")
    assert job.parameters == []
    compiled = compile_job(job, {one.id: one for one in first}, learned={}, ledger=(), broken=())
    assert "fixed_values" in [one.code for one in compiled.warnings]


async def test_a_job_the_sweep_cannot_bring_in_does_not_stop_the_next() -> None:
    uow = FakeUnitOfWork()
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(doing))
    await uow.workflows.save(_stored(doing, id="wfl_bad"))
    await uow.workflows.save(_stored(doing))
    ruling = uow.workflows.ruled

    async def _refuses_bad(tenant_id: TenantId, workflow_id: str, rule: int) -> bool:
        if workflow_id == "wfl_bad":
            raise RuntimeError("the store refused")
        return await ruling(tenant_id, workflow_id, rule)

    uow.workflows.ruled = _refuses_bad  # type: ignore[method-assign]

    await _swept(uow)

    assert uow.workflows.rules.get("wfl_ct") == K_PARAMETERS_RULE
    assert "wfl_bad" not in uow.workflows.rules


async def test_a_tenant_being_mined_elsewhere_is_brought_in_next_sweep() -> None:
    uow = FakeUnitOfWork()
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(doing))
    await uow.workflows.save(_stored(doing))
    locks = FakeAccountLocks()
    locks.busy.add("mining:acme")

    await _swept(uow, locks)

    assert "wfl_ct" not in uow.workflows.rules
    locks.busy.clear()
    await _swept(uow, locks)
    assert uow.workflows.rules["wfl_ct"] == K_PARAMETERS_RULE


async def test_a_job_that_always_fails_is_tried_a_bounded_number_of_times() -> None:
    uow = FakeUnitOfWork()
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(doing))
    await uow.workflows.save(_stored(doing, id="wfl_bad"))
    tried = 0

    async def _refuses(tenant_id: TenantId, workflow_id: str, rule: int) -> bool:
        nonlocal tried
        tried += 1
        raise RuntimeError("the store refused")

    uow.workflows.ruled = _refuses  # type: ignore[method-assign]
    reads = 0
    reading = uow.gestures.gestures_for

    async def _counted(*args: object, **kwargs: object) -> tuple[Gesture, ...]:
        nonlocal reads
        reads += 1
        return await reading(*args, **kwargs)

    sweeper = _sweeper(uow)
    for _ in range(K_BRING_IN_TRIES):
        await sweeper.execute(now=NOW)
    uow.gestures.gestures_for = _counted  # type: ignore[method-assign]
    await sweeper.execute(now=NOW)

    assert tried == K_BRING_IN_TRIES
    assert reads == 0, "a job given up on no longer costs a read of the evidence"


async def test_the_sweep_reads_only_the_readings_of_the_jobs_it_brings_in() -> None:
    uow = FakeUnitOfWork()
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    elsewhere = _doing("zz_a_", 900_000.0, ("Note", "unrelated"))
    await uow.gestures.add_gestures(tuple(doing + elsewhere))
    await uow.workflows.save(_stored(doing))
    asked: list[tuple[str, ...] | None] = []
    reading = uow.gestures.intents_for

    async def _spied(tenant_id: TenantId, *, ids: tuple[str, ...] | None = None) -> tuple:
        asked.append(ids)
        return await reading(tenant_id, ids=ids)

    uow.gestures.intents_for = _spied  # type: ignore[method-assign]

    await _swept(uow)

    assert asked and all(ids is not None and set(ids) <= {g.id for g in doing} for ids in asked)


async def test_a_job_whose_chore_flags_are_undecided_gets_the_rule_only_once_they_are() -> None:
    """It might be a chore: F3 decides sign-out after the job is stored, and a
    parameter minted meanwhile would stay on a chore for good."""
    uow = FakeUnitOfWork()
    doing = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(doing))
    await uow.workflows.save(_stored(doing, signs_out=None))

    assert await uow.workflows.behind_the_rule(K_PARAMETERS_RULE) == ()
    assert (
        await learn_parameters(
            uow,
            tenant_id=TENANT,
            known_id="wfl_ct",
            doings=(),
            by_id={one.id: one for one in doing},
            intents={},
            logins=Logins(),
        )
        == 0
    )
    assert (await uow.workflows.get(TENANT, "wfl_ct")).parameters == []
    assert "wfl_ct" not in uow.workflows.rules

    await uow.workflows.save(_stored(doing))
    await _swept(uow)
    assert uow.workflows.rules["wfl_ct"] == K_PARAMETERS_RULE
    assert "Customer Type" in _named(await uow.workflows.get(TENANT, "wfl_ct"))
