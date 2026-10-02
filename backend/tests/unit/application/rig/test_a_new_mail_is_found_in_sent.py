"""A new mail's Send click names its thread only by `thread-a:`.

Measured on QA 2026-09-28 (`wfl_5c702c71…`, `Compose and Send Email`): the
recorded Send carried 28 calls, 3 of them `/sync/u/N/i/s` POSTs, and their
bodies named the new mail only by `thread-a:` ids -- never `thread-f:`. So the
log said "1 named no thread" and the job's demonstrated recipient was never
granted. A new compose is simply shaped like that.

Held here: a Send click that names no `thread-f:` thread is looked up in the
operator's Sent mail through the Gmail tool, bounded to the click's window.
Exactly one sent mail there grants its recipients, as a thread-f match would;
none or several grant nobody, and the log says which in counts.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from sro.application.capture.rig_wire import Batch
from sro.application.context import RequestContext
from sro.application.execution.mail_job import Unaddressed, Written, write_the_mail
from sro.application.observation.correlate import correlate
from sro.application.ports.tools import ToolResult
from sro.domain.execution.mail_job import K_SEND_WINDOW_S
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))
T0 = 1_790_000_000.0
GMAIL = "https://mail.google.com/mail/u/0/#inbox?compose=new"
TO = "vendor@supplier.example"


def _stamp(at: float) -> str:
    return datetime.fromtimestamp(at, tz=UTC).isoformat().replace("+00:00", "Z")


def _sync(n: int, at: float) -> dict[str, Any]:
    """QA's shape: an `/i/s` POST whose bodies name the mail only by thread-a."""
    return {
        "kind": "request",
        "request": {
            "request_id": f"r{n}",
            "method": "POST",
            "url": "https://mail.google.com/sync/u/0/i/s?hl=en&c=51",
            "started_at": _stamp(at),
            "status": 200,
            "request_body": {"text": f'[["thread-a:r-{n}0417",[["msg-a:r-{n}0418"]]]]'},
            "response_body": {"text": f'[["thread-a:r-{n}0417",[["msg-a:r-{n}0418",1]]]]'},
        },
        "tab_id": 7,
    }


def _recorded_send() -> Gesture:
    batch = Batch.model_validate(
        {
            "batch_id": "bat_1",
            "device_id": "dev_1",
            "started_at": _stamp(T0 - 10),
            "ended_at": _stamp(T0 + 60),
            "events": [
                {
                    "kind": "gesture",
                    "gesture": {
                        "kind": "click",
                        "target": {
                            "tag": "div",
                            "role": "button",
                            "name": "Send ‪(⌘Enter)‬",
                        },
                        "at": T0,
                        "url": GMAIL,
                    },
                    "tab_id": 7,
                    "frame_url": GMAIL,
                    "page_url": GMAIL,
                },
                *(_sync(n, T0 + 0.2 * (n + 1)) for n in range(3)),
            ],
        }
    )
    (send,) = correlate(batch, f.TENANT.value)[0]
    assert len(send.requests) == 3 and "thread-f:" not in json.dumps(
        [(one.request_body, one.response_body) for one in send.requests], default=str
    )
    return send


def _compose(send: Gesture) -> Workflow:
    return Workflow(
        id="wfl_compose",
        tenant=f.TENANT.value,
        title="Compose and Send Email",
        narrative="the operator wrote a new mail and sent it",
        steps=[Step(order=0, says="Write the mail and press Send", system=None, cites=[send.id])],
    )


def _sent(message: str, *, at: float, to: str = TO, **more: object) -> dict[str, object]:
    return {"id": message, "sent": True, "sent_at": at, "to": to, **more}


class _Mailbox:
    """The operator's mailbox: Sent search, one message, one conversation."""

    def __init__(self, sent: list[dict[str, object]]) -> None:
        self.sent = sent
        self.queries: list[str] = []

    @property
    def available(self) -> bool:
        return True

    async def list_tools(self, tenant_id: TenantId, principal_id: PrincipalId, server: str) -> Any:
        return ()

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        if tool == "search_threads":
            self.queries.append(arguments["query"])
            words = dict(one.split(":", 1) for one in arguments["query"].split())
            after, before = float(words["after"]), float(words["before"])
            found = [
                {"id": one["id"], "from": "me", "subject": "Hi", "date": "", "snippet": ""}
                for one in self.sent
                if words.get("in") == "sent" and after <= float(str(one["sent_at"])) < before
            ]
            return ToolResult(text=json.dumps({"messages": found, "next_page": ""}))
        if tool == "get_message":
            one = next(m for m in self.sent if m["id"] == arguments["id"])
            return ToolResult(text=json.dumps({**one, "thread_id": f"t-{one['id']}"}))
        if tool == "get_thread":
            message = arguments["id"].removeprefix("t-")
            return ToolResult(
                text=json.dumps({"messages": [m for m in self.sent if m["id"] == message]})
            )
        return ToolResult(text="no such tool", failed=True)


async def _write(mailbox: _Mailbox, to: str = TO) -> Written | str:
    send = _recorded_send()
    return await write_the_mail(
        CTX,
        _compose(send),
        {},
        "",
        by_id={send.id: send},
        request=(),
        uow=FakeUnitOfWork(),
        tools=mailbox,
        asker=FakeAsker(Answer(data={"to": to, "subject": "Hi", "body": "Hi there.", "cited": []})),
        servers={},
    )


async def test_the_one_mail_sent_in_the_click_s_window_grants_its_recipients() -> None:
    mailbox = _Mailbox(
        [
            _sent("s-old", at=T0 - K_SEND_WINDOW_S - 60, to="old@supplier.example"),
            _sent("s-1", at=T0 + 2, to=f"Vendor <{TO}>", bcc="boss@wh.example"),
        ]
    )

    written = await _write(mailbox, f"{TO}, boss@wh.example")

    assert isinstance(written, Written)
    assert (written.to, written.bcc) == (TO, "boss@wh.example")
    (query,) = mailbox.queries
    assert query.split()[0] == "in:sent"
    assert isinstance(await _write(mailbox, "old@supplier.example"), Unaddressed)


@pytest.mark.parametrize(
    ("sent", "logged"),
    [
        ([], "1 named no thread, 1 looked up in Sent, 0 thread(s) read"),
        (
            [_sent("s-1", at=T0 + 2), _sent("s-2", at=T0 + 30, to="other@supplier.example")],
            "2 sent in the window; 0 found no sent mail, 1 found more than one, 0 granted",
        ),
        (
            [_sent("s-1", at=T0 + 2, marker="mk-ours")],
            "0 sent in the window; 1 found no sent mail",
        ),
    ],
)
async def test_none_or_several_in_sent_grant_nobody_and_say_which_in_counts(
    sent: list[dict[str, object]], logged: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        assert isinstance(await _write(_Mailbox(sent)), Unaddressed)

    assert logged in caplog.text
    assert "@" not in caplog.text
