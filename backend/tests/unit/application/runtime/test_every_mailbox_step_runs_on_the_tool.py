"""Every mailbox step of a run is the Gmail tool's, never the browser's.

Decided with the user 2026-09-28: mail work runs on the Gmail connector only.
A mailbox step that sends is the tool's send; one that only reads mail -- opens
it, searches, scrolls -- is read. One that changes the mailbox the tool cannot
change (label, archive, move) was marked "read" and skipped as if done; now the
run asks its operator in the panel to do it, and it never goes to the browser.

The structural signal is the recording's own: a mailbox gesture that made
Gmail's item-write call (`/sync/u/N/i/s`, the call a Send makes) changed the
mailbox. A mail row opened is still a read, and the typing and presses that
lead straight into a Send are that Send's, written by the writer.

Every gesture is recorded through `correlate`, and the run driven through
`RunSteps` over the real `ToolLane`.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from itertools import count
from typing import Any

from sro.application.capture.rig_wire import Batch
from sro.application.execution.mail_job import MailHand
from sro.application.observation.correlate import correlate
from sro.application.runtime.tool_lane import ToolLane
from sro.domain.chat.asked_by import by_hand
from sro.domain.execution.progress import Progress
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.runtime_support import _TENANT, CTX, _worker, steel_run

T0 = 1_790_000_000.0
INBOX = "https://mail.google.com/mail/u/0/#inbox"
THREAD = "https://mail.google.com/mail/u/0/#inbox/FMfcgzQXJWDhKq"
WMS = "https://wms.example/portal/customer-types"
ROW = "Alex R, New customer type, please set up NRT2 for the pilot"
_ids = count()


def _stamp(at: float) -> str:
    return datetime.fromtimestamp(T0 + at, tz=UTC).isoformat().replace("+00:00", "Z")


def _did(kind: str, page: str, at: float, name: str, *, value: str | None = None) -> dict[str, Any]:
    return {
        "kind": "gesture",
        "gesture": {
            "kind": kind,
            "target": {
                "tag": "div",
                "role": "textbox" if kind == "type" else "button",
                "name": name,
            },
            "value": value,
            "at": T0 + at,
            "url": page,
        },
        "tab_id": 1,
        "frame_url": page,
        "page_url": page,
    }


def _post(url: str, at: float) -> dict[str, Any]:
    return {
        "kind": "request",
        "request": {
            "request_id": f"r{next(_ids)}",
            "method": "POST",
            "url": url,
            "started_at": _stamp(at),
            "status": 200,
        },
        "tab_id": 1,
    }


def _recorded(*events: dict[str, Any]) -> dict[str, Gesture]:
    batch = Batch.model_validate(
        {
            "batch_id": f"bat_{next(_ids)}",
            "device_id": "dev_1",
            "started_at": _stamp(0),
            "ended_at": _stamp(600),
            "events": list(events),
        }
    )
    return {one.id: one for one in correlate(batch, _TENANT)[0]}


WRITE = "https://mail.google.com/sync/u/0/i/s?hl=en&c=7"


def _opened(at: float = 1) -> dict[str, Gesture]:
    """QA's shape: a mail row clicked, which POSTs `?ui=2` -- not a write."""
    return _recorded(
        _did("click", INBOX, at, ROW), _post("https://mail.google.com/mail/u/0/?ui=2", at + 0.2)
    )


def _archived(at: float = 20) -> dict[str, Gesture]:
    return _recorded(_did("click", THREAD, at, "Archive"), _post(WRITE, at + 0.2))


def _labelled(at: float = 40) -> dict[str, Gesture]:
    return _recorded(
        _did("click", THREAD, at, "Labels"),
        _did("click", THREAD, at + 2, "Pilots"),
        _post(WRITE, at + 2.2),
    )


def _step(order: int, says: str, cited: dict[str, Gesture]) -> Step:
    return Step(order=order, says=says, system=None, cites=list(cited))


def _job(*steps: tuple[str, dict[str, Gesture]]) -> tuple[Workflow, dict[str, Gesture]]:
    job = Workflow(
        id="wfl_1",
        tenant=_TENANT,
        title="t",
        narrative="n",
        steps=[_step(n, says, cited) for n, (says, cited) in enumerate(steps)],
    )
    return job, {one: seen for _, cited in steps for one, seen in cited.items()}


def test_a_step_that_changed_the_mailbox_is_by_hand_and_one_that_read_it_is_not() -> None:
    job, by_id = _job(
        ("Open the request", _opened()),
        ("Archive it", _archived()),
        ("Label it Pilots", _labelled()),
        ("Save it in the WMS", _recorded(_did("click", WMS, 60, "Save"))),
    )

    assert [by_hand(job, step, by_id) for step in job.steps] == [False, True, True, False]


def test_what_leads_straight_into_a_send_is_the_send_s() -> None:
    """A reply clicked and its body typed -- the draft saved as it is typed,
    which is the same write call -- are the mail the Send step writes."""
    job, by_id = _job(
        ("Open the request", _opened()),
        ("Click Reply", _recorded(_did("click", THREAD, 20, "Reply"))),
        (
            "Type the answer",
            _recorded(_did("type", THREAD, 30, "Message Body", value="Done."), _post(WRITE, 31)),
        ),
        (
            "Press Send",
            _recorded(_did("click", THREAD, 40, "Send ‪(⌘Enter)‬"), _post(WRITE, 40.2)),
        ),
        ("Archive it", _archived(60)),
    )

    assert [by_hand(job, step, by_id) for step in job.steps] == [False, False, False, False, True]


def _no_mail(_: object) -> MailHand:
    async def never(*_: object) -> Any:
        raise AssertionError("no mail is written or sent for a step that sends none")

    return MailHand(write=never, send=never)


async def test_a_run_reads_the_mail_asks_for_the_archive_and_never_opens_a_browser() -> None:
    steps = [("Open the request", _opened()), ("Archive it", _archived())]
    world = await steel_run(
        steps=[(_step(0, says, cited), cited) for says, cited in steps], recorded_sign_in=False
    )
    run_steps = _worker(
        world.uow, world.driver, world.vault, world.clock, world.lanes, tool=ToolLane(_no_mail)
    )[1]

    prepared = await run_steps.prepare(CTX, world.run_id)
    read = await run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    asked = await run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert not prepared.browser, "no browser is held for mailbox steps"
    assert read.more and not read.asking
    assert asked.asking
    asking = Progress.of((await world.saved_run()).progress).asking
    assert asking["kind"] == "step" and "mail tool cannot" in asking["text"]
    assert (world.lanes.ui.calls, world.lanes.sight.calls, world.lanes.api.calls) == (0, 0, 0)

    world.run_steps = run_steps
    await world.answer(asking["id"], verdict="done")

    done = await world.saved_run()
    last = done.steps[-1]
    assert (last.of_step, last.verdict, last.verdict_by) == (1, "held", "operator")


async def test_an_archive_the_operator_says_was_not_done_is_asked_again() -> None:
    steps = [("Archive it", _archived())]
    world = await steel_run(
        steps=[(_step(0, says, cited), cited) for says, cited in steps], recorded_sign_in=False
    )
    world.run_steps = _worker(
        world.uow, world.driver, world.vault, world.clock, world.lanes, tool=ToolLane(_no_mail)
    )[1]
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    first = Progress.of((await world.saved_run()).progress).asking

    await world.answer(first["id"], verdict="not_done")
    again = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    second = Progress.of((await world.saved_run()).progress).asking
    assert again.asking and second["kind"] == "step" and second["id"] != first["id"]
    assert world.lanes.ui.calls == 0
