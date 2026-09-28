"""A doing that is nothing but mail is covered by the Gmail tool, like a chore.

Decided with the user 2026-09-28: mail work runs on the Gmail connector only.
A mined job whose every step is on the mailbox (`is_mail_only`) is flagged in
code from its evidence -- never retired, so its demonstrated recipients stay
usable -- and is never offered and never a mining eval case. A mail step inside
a larger doing stays a step of that job.

Every gesture is recorded through `correlate`, the ingest path production uses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from typing import Any

from evals.suites.mining import Mining

from sro.application.capture.rig_wire import Batch
from sro.application.chat.read_chat import ReadChat
from sro.application.context import RequestContext
from sro.application.observation.correlate import correlate
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork

T0 = 1_790_000_000.0
NOW = datetime.fromtimestamp(T0 + 3600, tz=UTC)
GMAIL = "https://mail.google.com/mail/u/0/#inbox"
WMS = "https://wms.example/portal/customer-types"
_ids = count()


def _stamp(at: float) -> str:
    return datetime.fromtimestamp(T0 + at, tz=UTC).isoformat().replace("+00:00", "Z")


def _click(page: str, at: float, name: str) -> dict[str, Any]:
    return {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "target": {"tag": "div", "role": "button", "name": name},
            "at": T0 + at,
            "url": page,
        },
        "tab_id": 1,
        "frame_url": page,
        "page_url": page,
    }


def _recorded(*events: dict[str, Any]) -> list[Gesture]:
    batch = Batch.model_validate(
        {
            "batch_id": f"bat_{next(_ids)}",
            "device_id": "dev_1",
            "started_at": _stamp(0),
            "ended_at": _stamp(600),
            "events": list(events),
        }
    )
    return correlate(batch, f.TENANT.value)[0]


def _job(id_: str, title: str, gestures: list[Gesture]) -> Workflow:
    return Workflow(
        id=id_,
        tenant=f.TENANT.value,
        title=title,
        narrative=title,
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[one.id])
            for n, one in enumerate(gestures)
        ],
        signs_in=False,
        signs_out=False,
    )


async def _world() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    mail = _recorded(_click(GMAIL, 1, "Compose"), _click(GMAIL, 20, "Send ‪(⌘Enter)‬"))
    mixed = _recorded(
        _click(GMAIL, 100, "Alex R, New customer type, please set up NRT2 for the pilot"),
        _click(WMS, 130, "Save"),
    )
    async with uow:
        await uow.gestures.add_gestures((*mail, *mixed))
        await uow.workflows.save(_job("wfl_mail", "Compose and Send Email", mail))
        await uow.workflows.save(_job("wfl_mixed", "Create a Customer Type", mixed))
        await uow.commit()
    return uow


async def test_a_mail_only_job_is_never_a_candidate_and_a_mixed_one_still_is() -> None:
    uow = await _world()
    asker = FakeAsker(Answer(data={"job": None, "sure": False}))

    await ReadChat(uow, asker=asker, clock=FakeClock(NOW), cap_usd=5.0).execute(
        RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh")),
        utterance="compose and send an email about the customer type",
    )

    shown = str(asker.asked[0]["evidence"])
    assert "wfl_mixed" in shown
    assert "wfl_mail" not in shown
    assert [one.id for one in await uow.workflows.known(f.TENANT)] == ["wfl_mail", "wfl_mixed"]


async def test_a_mail_only_job_is_never_a_mining_eval_case() -> None:
    uow = await _world()

    cases = await Mining().cases(uow, f.TENANT)

    assert [one.id for one in cases] == ["wfl_mixed"]
