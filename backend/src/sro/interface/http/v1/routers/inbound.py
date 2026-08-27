"""The door a mail relay or a chat webhook knocks on.

No tenant credential reaches this far -- there is nobody signed in on the
other end of an email. A per-trigger token, presented as a header, stands in
for one. Routers never catch domain errors (see `errors.py`); `InboundRefused`
is mapped there like every other one.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Header, status

from sro.domain.shared.identifiers import TriggerId
from sro.interface.http.deps import ContainerDep
from sro.interface.http.schemas import FiredModel

router = APIRouter(prefix="/inbound", tags=["inbound"])


@router.post("/{trigger_id}", status_code=status.HTTP_202_ACCEPTED)
async def receive_inbound(
    trigger_id: str,
    container: ContainerDep,
    x_inbound_token: Annotated[str, Header()],
    message: Annotated[dict[str, Any], Body()] = {},  # noqa: B006
) -> FiredModel:
    """The body is whatever the relay sends -- a mailbox rule's template, a
    webhook's payload -- and it is read, not trusted: the trigger takes from it
    only the parameters it declared. Unknown fields are ignored rather than
    refused, so a relay adding one to its payload is not a reason for a mailbox
    rule that has worked for a year to start returning 422. A field whose value
    is not a single value -- a list of recipients, a nested envelope -- is not a
    parameter either, and is dropped here rather than reaching the run as the
    string `['a', 'b']`."""
    fired = await container.receive_inbound().execute(
        TriggerId(trigger_id),
        token=x_inbound_token,
        message={
            name: str(value)
            for name, value in message.items()
            if isinstance(value, str | int | float | bool)
        },
    )
    return FiredModel(
        trigger_id=fired.trigger_id.value,
        run_id=fired.run_id.value if fired.run_id else None,
        skipped=fired.skipped,
    )
