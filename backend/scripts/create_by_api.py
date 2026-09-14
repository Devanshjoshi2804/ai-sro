"""Create a record straight through the API, in the operator's own session.

The question this answers: the job was demonstrated by clicking through a form,
and the same record can be made with one call -- so make it with one call, with
values somebody chose rather than the ones the recording happened to carry.

    uv run python scripts/create_by_api.py new workAreas \
        --set workArea=APITEST1 --set workAreaDescription="made by api"
    ... --send        # actually send it

**Nothing is replayed from the recording but the SHAPE.** Blue Yonder signs
every write with a `CSRF-ENCRYPT-TOKEN` that the recorder strikes out at the
boundary, so a byte-for-byte replay is refused before it is routed. The
extension fetches that header off the live page instead and sends the call from
inside the tab the operator is signed into -- `credentials: "include"` -- which
is why this needs a connected browser and not a credential in a file.

Two gates, and neither is this script's to relax:

**The ledger.** `verified_write_for` refuses a `(method, path)` this deployment
has not individually watched succeed -- edit, verify on a separate read,
revert. `knowledge-base/index/write-endpoints.json` is that record.

**The browser.** The call goes out through the extension's `http.send`, so it
is the operator's own session doing it, from a page they are already on.

Dry by default, and the dry run prints the whole request: url, headers, the
body with the values substituted, and which headers the extension will fill in
live. A write to a warehouse is not something to send on a flag somebody typed
by accident.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from sro.application.capture.rig_wire import headers_without_markers
from sro.container import build_container
from sro.domain.execution.planning import LIVE_FETCHABLE_HEADERS
from sro.domain.execution.verified_writes import verified_write_for
from sro.domain.observation.gesture import Call
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.identifiers import DeviceId, TenantId


def _newest(calls: list[Call]) -> Call | None:
    """The most recent create of this resource that the system answered 2xx.

    Newest because a form changes: the last one that worked is the one whose
    body has the fields the system wants today.
    """
    worked = [
        call
        for call in calls
        if call.status is not None and 200 <= call.status < 300 and not call.failure_reason
    ]
    return max(worked, key=lambda call: call.started_at or 0.0) if worked else None


async def _make(
    tenant: str, resource: str, values: dict[str, str], *, send: bool, device: str | None
) -> int:
    container = build_container()
    tenant_id = TenantId(tenant)
    async with container.unit_of_work() as uow:
        gestures = await uow.gestures.gestures_for(tenant_id)

    found = [
        call
        for gesture in gestures
        for call in gesture.requests
        if call.method.upper() == "POST" and f"/{resource}" in (call.url or "").split("?")[0]
    ]
    call = _newest(found)
    if call is None:
        print(f"no create of {resource!r} that this store ever saw succeed")
        return 2

    allowed = verified_write_for(call, container.start_workflow_run()._verified_writes)
    if allowed is None:
        print(f"{call.method} {call.url.split('?')[0]} is not in the verified-writes ledger")
        print("   nothing sends a write this deployment has not watched succeed and revert")
        return 1

    body = (
        json.loads(call.request_body.text) if call.request_body and call.request_body.text else {}
    )
    unknown = sorted(set(values) - set(body))
    if unknown:
        print(f"the recorded body has no {', '.join(unknown)}. It has: {', '.join(sorted(body))}")
        return 1
    body.update(values)

    headers = headers_without_markers(call.request_headers)
    live = [
        name
        for name, value in call.request_headers.items()
        if REDACTED in value and name.lower() in LIVE_FETCHABLE_HEADERS
    ]
    struck = [
        name
        for name, value in call.request_headers.items()
        if REDACTED in value and name.lower() not in LIVE_FETCHABLE_HEADERS
    ]

    print(f"POST {call.url}")
    print(f"   allowed by the ledger as {allowed.path_pattern}")
    for name, value in headers.items():
        print(f"   {name}: {value}")
    for name in live:
        print(f"   {name}: <the extension reads this off the live page>")
    for name in struck:
        print(f"   {name}: STRUCK OUT AND NOT SENT -- the server may refuse the call for it")
    print(f"   body: {json.dumps(body)}")
    print(f"   changed: {', '.join(f'{k}={v}' for k, v in values.items()) or 'nothing'}")

    if not send:
        print("\ndry. Add --send to put this into the warehouse.")
        return 0

    online = container.agent_sockets.online(tenant_id)
    if not online:
        # Not "no browser is connected" -- one may well be, and `/v1/agents`
        # will say `online: true` while this prints. The socket is held by
        # whichever process the extension connected to, which is the API, and
        # this script is not that process. The same wall the Temporal worker
        # hit: it asks the API through `RunDispatcher` rather than reaching for
        # a browser it cannot see.
        #
        # There is no equivalent door for a bare command, on purpose.
        # `docs/14-extension-protocol.md`: an internal "send this browser a
        # command" route would be a way to drive somebody's signed-in session
        # anywhere, which no taught skill may do. A command reaches a browser
        # as part of a RUN or not at all.
        print(
            "\nthis process holds no socket to a browser -- the API does."
            "\nThe request above is correct and the extension can make it; what"
            "\ncannot happen is this script sending it. Start a run of a job whose"
            "\nstep replays this call -- POST /v1/workflow-runs, or the offer in"
            "\nthe panel -- and the same request goes out in the operator's session."
        )
        return 1
    chosen = DeviceId(device) if device else online[0]
    payload: dict[str, Any] = {
        "method": "POST",
        "url": call.url,
        "headers": headers,
        "body": json.dumps(body),
    }
    if live:
        payload["live_headers"] = live

    print(f"\nsending it through {chosen.value}")
    reply = await container.agent_sockets.send(
        tenant_id, chosen, kind="http.send", payload=payload, deadline_s=60.0
    )
    print(f"   ok={reply.ok}")
    print(f"   result={json.dumps(reply.result)[:400] if reply.ok else reply.error}")
    return 0 if reply.ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tenant")
    parser.add_argument("resource", help="the path segment: workAreas, customerTypes, suppliers …")
    parser.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE")
    parser.add_argument(
        "--device", default=None, help="which browser; the first connected one by default"
    )
    parser.add_argument("--send", action="store_true", help="actually send it")
    args = parser.parse_args()
    values = dict(pair.split("=", 1) for pair in args.set)
    return asyncio.run(
        _make(args.tenant, args.resource, values, send=args.send, device=args.device)
    )


if __name__ == "__main__":
    raise SystemExit(main())
