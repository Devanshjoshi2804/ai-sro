"""What the chat and the mail door offer: real jobs only.

Measured on greyorange (2026-09-28): "Navigate to Receiving" was offered 17
times and expired 16; two "Create a Customer Type" copies were offered side by
side; and typing a title back to "Did you mean X or Y?" asked the same again.
Every test here goes through `ReadChat` with jobs stored as mining stores them:
a workflow row and the gestures its steps cite.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sro.application.chat.read_chat import ReadChat
from sro.application.chat.understand import Understood
from sro.application.context import RequestContext
from sro.application.skill.read_workflows import ReadWorkflows
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.schemas import WorkflowsResponse
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork
from tests.unit.runtime_support import mail_send_step, read_step, save_step

TENANT = TenantId("acme")
NOW = datetime(2025, 2, 11, 12, 0, tzinfo=UTC)


async def _stored(
    uow: FakeUnitOfWork, id_: str, title: str, step: Step, by_id: dict[str, Gesture]
) -> None:
    await uow.workflows.save(
        Workflow(
            id=id_,
            tenant=TENANT.value,
            title=title,
            narrative="",
            steps=[replace(step, order=0)],
        )
    )
    await uow.gestures.add_gestures(
        tuple(replace(one, tenant=TENANT.value) for one in by_id.values())
    )


async def _read(uow: FakeUnitOfWork, asker: FakeAsker, said: str) -> Understood:
    ctx = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("operator"))
    return await ReadChat(uow.hand_out(), asker=asker, clock=FakeClock(NOW), cap_usd=-1).execute(
        ctx, utterance=said
    )


def _offered(asker: FakeAsker) -> str:
    return str(asker.asked[0]["evidence"]).split('<untrusted name="candidates">', 1)[1]


async def test_a_click_through_that_writes_nothing_is_never_offered() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow, "wfl_ct", "Create a Customer Type", *save_step(gid="ges_ct"))
    await _stored(uow, "wfl_nav", "Navigate to Receiving", *read_step())
    asker = FakeAsker(Answer(data={"job": None, "sure": False, "values": []}))

    await _read(uow, asker, "navigate to receiving")

    assert "wfl_ct" in _offered(asker)
    assert "wfl_nav" not in _offered(asker), "a fragment that writes nothing was offered"


async def test_of_two_copies_the_one_that_writes_is_offered() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow, "wfl_a", "Create a Customer Type", *save_step(gid="ges_a"))
    stub, seen = read_step()
    await _stored(uow, "wfl_b", "Create a Customer Type", stub, seen)
    await uow.workflows.save(
        replace(await uow.workflows.get(TENANT, "wfl_b"), parameters=[{"name": "Customer Type"}])
    )
    asker = FakeAsker(Answer(data={"job": None, "sure": False, "values": []}))

    await _read(uow, asker, "new customer type GT7")

    assert "wfl_a" in _offered(asker) and "wfl_b" not in _offered(asker)


async def test_an_exact_title_typed_back_picks_that_job() -> None:
    uow = FakeUnitOfWork()
    await _stored(uow, "wfl_c", "Create a Customer Type", *save_step(gid="ges_c"))
    await _stored(uow, "wfl_d", "Delete a Customer Type", *save_step(gid="ges_d"))
    unsure = Answer(data={"job": "wfl_d", "sure": False, "also": ["wfl_c"], "values": []})
    asker = FakeAsker(unsure, unsure)

    got = await _read(uow, asker, "  delete a customer TYPE ")

    assert got.workflow_id == "wfl_d" and got.sure and not got.also
    assert asker.asked == [], "an exact title is a pick, not a question for the model"


async def test_the_panel_s_list_marks_only_real_jobs_offered_and_keeps_every_job() -> None:
    """Seen on QA (2026-09-29): the panel's "Learned from what you do here" listed
    Reply to Email and Forward Email. The listing is the console's too, so every
    job stays on it; `offered` is the chat's own rule, read once."""
    uow = FakeUnitOfWork()
    await _stored(uow, "wfl_ct", "Create a Customer Type", *save_step(gid="ges_ct"))
    await uow.workflows.save(
        replace(await uow.workflows.get(TENANT, "wfl_ct"), parameters=[{"name": "Customer Type"}])
    )
    await _stored(uow, "wfl_ct_copy", "create a customer  type", *save_step(gid="ges_ct2"))
    await _stored(uow, "wfl_nav", "Navigate to Receiving", *read_step())
    await _stored(uow, "wfl_mail", "Reply to Email", *mail_send_step())
    await _stored(uow, "wfl_in", "Log in to Keycloak", *save_step(gid="ges_in"))
    await uow.workflows.decide(
        TENANT, await uow.workflows.get(TENANT, "wfl_in"), signs_in=True, signs_out=False
    )
    ctx = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("operator"))

    listed = WorkflowsResponse.of(
        await ReadWorkflows(uow.hand_out(), FakeClock(NOW)).execute(ctx)
    ).workflows

    assert {one.id: one.offered for one in listed} == {
        "wfl_ct": True,
        "wfl_ct_copy": False,
        "wfl_nav": False,
        "wfl_mail": False,
        "wfl_in": False,
    }
