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

from sro.application.observation.mine_lately import MineLately
from sro.application.observation.mining_pass import MineResult, mine
from sro.domain.execution.compiled import compile_job
from sro.domain.observation.gesture import Action, Body, Call, Component, Gesture, Target
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.learned import K_PARAMETERS_RULE
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
                component=Component(field_label=label) if label and not secret else None,
            ),
        ),
        requests=requests,
    )


def _customer_type(n: str, at: float, code: str, says: str, bill_to: str) -> list[Gesture]:
    """One doing, eleven steps: four typed values, the operator's own username
    typed into a box, and a password confirmed."""
    return [
        _gesture(f"{n}00", at + 0, "click", label="Masters"),
        _gesture(f"{n}01", at + 1, "click", label="Customer Types"),
        _gesture(f"{n}02", at + 2, "click", label="New"),
        _gesture(f"{n}03", at + 3, "type", label="Customer Type", value=code, required=True),
        _gesture(f"{n}04", at + 4, "type", label="Description", value=says),
        _gesture(f"{n}05", at + 5, "type", label="Short Description", value=code[:2]),
        _gesture(f"{n}06", at + 6, "select", label="Bill To", value=bill_to),
        _gesture(f"{n}07", at + 7, "type", label="Created By", value=USERNAME),
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
    await uow.workflows.save(_signing_in_job("h", signs_in=True))


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
    job = _signing_in_job("h", signs_in=True)
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


async def test_a_value_one_doing_could_not_tell_from_a_constant_is_fixed_by_the_next() -> None:
    uow = FakeUnitOfWork()
    first = _customer_type("ct_a_", 5000.0, "GT7", "Ground transport", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(first))
    await _mine(uow, _proposed(first))
    assert "Bill To" in _named(await _work(uow))
    again = _customer_type("ct_b_", 90_000.0, "RL2", "Rail", "Bill-To Customer")
    await uow.gestures.add_gestures(tuple(again))

    await _mine(uow, _proposed(again))

    named = _named(await _work(uow))
    assert "Bill To" not in named and "Created By" not in named
    assert named["Customer Type"] == ["GT7", "RL2"]


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
        ),
        **over,
    )


async def _swept(uow: FakeUnitOfWork, locks: FakeAccountLocks | None = None) -> None:
    class _Nothing:
        async def execute(self, ctx: object) -> MineResult:
            return MineResult()

    class _NothingRead:
        async def execute(self, ctx: object) -> int:
            return 0

    await MineLately(
        uow, _Nothing(), _NothingRead(), locks or FakeAccountLocks(), window_hours=24
    ).execute(now=NOW)


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
