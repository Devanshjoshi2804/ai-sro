from __future__ import annotations

import asyncio
from collections.abc import Mapping

from sro.application.execution.mail_job import Written
from sro.application.runtime.step import Held, LaneContext
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow

GMAIL = "https://mail.google.com/mail/u/0/#inbox"


def mail_send_step() -> tuple[Step, dict[str, Gesture]]:
    gesture = Gesture(
        id="g-send",
        tenant="t1",
        stream_id="str-1",
        batch_id="bat-1",
        at=1_000.0,
        url=GMAIL,
        system=GMAIL,
        tab_id=7,
        frame_url=None,
        action=Action(
            kind="click",
            at=1_000.0,
            url=GMAIL,
            target=Target(tag="button", role="button", name="Send"),
        ),
    )
    step = Step(order=0, says="Send the mail", system=None, cites=["g-send"])
    return step, {"g-send": gesture}


async def write_ok(workflow: Workflow, values: Mapping[str, str], thread: str) -> Written | str:
    return Written(to="ops@example.com", subject="s", body="b", thread=thread, in_reply_to="")


async def _sent(sent: list[Written], mail: Written, msg_id: str) -> tuple[str, str]:
    sent.append(mail)
    return msg_id, ""


async def _answer(msg_id: str, why: str) -> tuple[str, str]:
    return msg_id, why


def lane_context(
    by_id: Mapping[str, Gesture], *, held: Held | None, thread: str = ""
) -> LaneContext:
    return LaneContext(
        tenant_id=TenantId("t1"),
        principal_id=PrincipalId("p1"),
        workflow=Workflow(id="wf_1", tenant="t1", title="t", narrative="n"),
        by_id=by_id,
        learned={},
        ledger=(),
        held=held,
        stop=asyncio.Event(),
        thread=thread,
    )
