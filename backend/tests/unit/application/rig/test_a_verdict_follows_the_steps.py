"""Whether a job signs in or out is re-decided whenever its steps change.

The verdict was written once, when a proposal was stored, and every later
grow, heal or learn either carried a stale one along in a whole-job save or
left it alone. Each of them now decides again from the evidence, and writes
only the two columns, over the job exactly as it read it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sro.application.context import RequestContext
from sro.application.observation.mine_lately import MineLately
from sro.application.observation.mining_pass import MineResult, _grow, fill_in_passwords, mine
from sro.application.runtime.teach import Teach
from sro.domain.execution.compose import Composed
from sro.domain.execution.lanes import Lane
from sro.domain.observation.driving import WAS_OUR_OWN_DRIVING
from sro.domain.observation.gesture import Action, Call, Gesture, Intent, PageMark, Target
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import FakeAccountLocks, FakeAsker, FakeClock, FakeUnitOfWork

TENANT = TenantId("acme")
CTX = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("clerk"))
KEYCLOAK = "https://keycloak.example"
WMS = "https://wms.example"


def _gesture(gesture_id: str, at: float, url: str, action: Action, **more: object) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=TENANT.value,
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{url}/page",
        system=url,
        tab_id=1,
        frame_url=None,
        action=action,
        **more,
    )


def _signing_in() -> dict[str, Gesture]:
    """A click on the sign-in form, the password typed (never cited: redaction
    leaves a model nothing to point at), and the submit that hands the browser
    on to the warehouse."""
    return {
        "a": _gesture("a", 1, KEYCLOAK, Action(kind="click", at=1, target=Target(name="User"))),
        "b": _gesture("b", 2, KEYCLOAK, Action(kind="type", at=2, secret=True)),
        "c": _gesture(
            "c",
            3,
            KEYCLOAK,
            Action(kind="press", at=3, target=Target(name="Sign In")),
            requests=[Call(method="POST", url=f"{KEYCLOAK}/login", status=302)],
            page_events=[PageMark(at=3, page_kind="navigated", url=f"{WMS}/home")],
        ),
    }


def _logging_out() -> dict[str, Gesture]:
    return {
        "menu": _gesture(
            "menu", 1, WMS, Action(kind="click", at=1, target=Target(role="menuitem", name="admin"))
        ),
        "out": _gesture(
            "out",
            2,
            WMS,
            Action(kind="click", at=2, target=Target(role="menuitem", name="Log Out")),
            page_events=[PageMark(at=2, page_kind="navigated", url=f"{WMS}/login")],
        ),
    }


def _job(job_id: str, *cites: str, **over: object) -> Workflow:
    return Workflow(
        id=job_id,
        tenant=TENANT.value,
        title="t",
        narrative="n",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[one]) for n, one in enumerate(cites)
        ],
        **over,
    )


async def test_a_job_whose_grow_adds_sign_in_steps_flips_to_signing_in() -> None:
    """The stored job had only the click on the form, which signs nobody in; the
    doing it grows into types the password and leaves. The verdict comes from
    that evidence, not from whatever the proposal carried."""
    uow = FakeUnitOfWork()
    by_id = _signing_in()
    await uow.gestures.add_gestures(tuple(by_id.values()))
    await uow.workflows.save(_job("wfl_kc", "a", signs_in=False, signs_out=False))

    await _grow(
        uow, tenant_id=TENANT, known_id="wfl_kc", proposal=_job("wfl_new", "a", "c"), by_id=by_id
    )

    grown = await uow.workflows.get(TENANT, "wfl_kc")
    assert [step.cites for step in grown.steps] == [["a"], ["c"]]
    assert (grown.signs_in, grown.signs_out) == (True, False)


async def test_a_heal_decides_a_stale_verdict_and_counts_the_job_once() -> None:
    uow = FakeUnitOfWork()
    by_id = _logging_out()
    await uow.gestures.add_gestures(tuple(by_id.values()))
    await uow.workflows.save(_job("wfl_out", "menu", "out", signs_in=False, signs_out=False))

    assert await fill_in_passwords(uow, tenant_id=TENANT) == 1
    assert await fill_in_passwords(uow, tenant_id=TENANT) == 0

    healed = await uow.workflows.get(TENANT, "wfl_out")
    assert (healed.signs_in, healed.signs_out) == (False, True)


async def test_a_learned_field_decides_the_verdict_of_the_steps_it_made() -> None:
    uow = FakeUnitOfWork()
    by_id = _logging_out()
    await uow.gestures.add_gestures(tuple(by_id.values()))
    job = _job("wfl_out", "menu", "out", signs_in=False, signs_out=False)
    await uow.workflows.save(job)

    await Teach(uow, FakeClock()).learn_field(
        CTX,
        job,
        Composed("site", "Site", "combobox", 1),
        key="site",
        value="x",
        learned={},
        lane=Lane.UI,
        run_id="run_1",
    )

    learned = await uow.workflows.get(TENANT, "wfl_out")
    assert [step.says for step in learned.steps] == ["step 0", "Fill Site", "step 1"]
    assert (learned.signs_in, learned.signs_out) == (False, True)


async def test_a_learn_that_changed_nothing_decides_nothing() -> None:
    uow = FakeUnitOfWork()
    job = _job("wfl_out", "menu", "out", signs_in=False, signs_out=False)
    await uow.workflows.save(replace(job, steps=[*job.steps, Step(2, "more", None, ["x"])]))

    await Teach(uow, FakeClock()).learn_field(
        CTX,
        job,
        Composed("site", "Site", "combobox", 1),
        key="site",
        value="x",
        learned={},
        lane=Lane.UI,
        run_id="run_1",
    )

    assert uow.gestures.gestures_for_calls == 0


async def test_the_sweep_and_the_heal_judge_the_same_gestures_so_the_verdict_holds() -> None:
    """The password is typed in the same burst as the job's first cited click,
    at the same instant. The heal read every gesture the tenant has; the
    sweep read `at > first` and missed it. The two came to opposite verdicts,
    and a job flipped between passes."""
    uow = FakeUnitOfWork()
    by_id = _signing_in()
    by_id["b"] = replace(by_id["b"], at=1, action=Action(kind="type", at=1, secret=True))
    await uow.gestures.add_gestures(tuple(by_id.values()))
    await uow.workflows.save(_job("wfl_kc", "a", "c"))

    await MineLately(
        uow, _NoPass(), _NoRead(), FakeAccountLocks(), window_hours=24, max_reads=1
    ).execute(now=datetime(2026, 9, 27, tzinfo=UTC))
    swept = await uow.workflows.get(TENANT, "wfl_kc")

    assert (swept.signs_in, swept.signs_out) == (True, False)
    await fill_in_passwords(uow, tenant_id=TENANT)
    healed = await uow.workflows.get(TENANT, "wfl_kc")
    assert (healed.signs_in, healed.signs_out) == (True, False)


class _NoPass:
    async def execute(self, ctx: RequestContext) -> MineResult:
        raise AssertionError("nothing was captured lately, so nothing is mined")


class _NoRead:
    async def execute(self, ctx: RequestContext) -> int:
        return 0


async def test_a_new_job_is_first_judged_against_what_the_heal_will_judge_it_against() -> None:
    """The operator logs out; this browser's own driving then signs the
    session back in -- a credential on the sign-in page, marked as ours and
    left out of the pass's window. The pass judged the proposal without that
    gesture (no sign the session ended: `False`) and the next heal, which
    reads every gesture, judged it `True`: the verdict flipped between passes."""
    uow = FakeUnitOfWork()
    by_id = _logging_out()
    by_id["out"] = replace(by_id["out"], page_events=[])
    by_id["again"] = _gesture(
        "again",
        4,
        WMS,
        Action(kind="type", at=4, secret=True, target=Target(name="password", secret=True)),
    )
    await uow.gestures.add_gestures(tuple(by_id.values()))
    await uow.gestures.save_intent(
        Intent(gesture_id="again", tenant=TENANT.value, why=WAS_OUR_OWN_DRIVING)
    )
    step = {"cites": [], "system": WMS, "parameters": []}
    proposal = {
        "title": "Log Out",
        "narrative": "the operator logged out",
        "systems": [WMS],
        "steps": [
            {**step, "order": 0, "cites": ["menu"], "says": "open the user menu"},
            {**step, "order": 1, "cites": ["out"], "says": "click Log Out"},
        ],
        "parameters": [],
    }

    await mine(
        uow,
        tenant_id=TENANT,
        asker=FakeAsker(Answer(data={"workflows": [proposal]}, cost_usd=0.01)),
        locks=FakeAccountLocks(),
        now=datetime(2026, 9, 27, tzinfo=UTC),
        cap_usd=100.0,
    )
    (kept,) = await uow.workflows.known(TENANT)

    assert (kept.signs_in, kept.signs_out) == (False, True)
    await fill_in_passwords(uow, tenant_id=TENANT)
    healed = await uow.workflows.get(TENANT, kept.id)
    assert (healed.signs_in, healed.signs_out) == (False, True)
