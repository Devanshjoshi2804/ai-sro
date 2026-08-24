"""The door a mail relay or a chat webhook knocks on.

No tenant credential reaches this far -- there is nobody signed in on the
other end of an email. A per-trigger token, presented as a header, stands in
for one. Routers never catch domain errors (see `errors.py`); `InboundRefused`
is mapped there like every other one.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, status

from sro.domain.shared.identifiers import TriggerId
from sro.interface.http.deps import ContainerDep
from sro.interface.http.schemas import FiredModel

router = APIRouter(prefix="/inbound", tags=["inbound"])


@router.post("/{trigger_id}", status_code=status.HTTP_202_ACCEPTED)
async def receive_inbound(
    trigger_id: str,
    container: ContainerDep,
    x_inbound_token: Annotated[str, Header()],
) -> FiredModel:
    fired = await container.receive_inbound().execute(TriggerId(trigger_id), token=x_inbound_token)
    return FiredModel(
        trigger_id=fired.trigger_id.value,
        run_id=fired.run_id.value if fired.run_id else None,
        skipped=fired.skipped,
    )
