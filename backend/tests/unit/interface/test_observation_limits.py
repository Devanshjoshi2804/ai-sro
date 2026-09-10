"""Two size belts on the door a browser extension writes through.

`POST /v1/observations` and `POST /v1/observations/artifacts` take an
authenticated but *operator-controlled* payload: whatever the extension on
somebody's laptop decides to send. Before this, the batch route took an event
list of any length and the artifact route read the whole upload into memory
with `await file.read()`. Both belts are the rig's, with the rig's numbers
(`new_agent_arch/src/rig/api.py:374`, `:379`).

Both boundaries are asserted from both sides. `>` and `>=` differ by exactly
one event, and a test that sends ten times the limit passes under either -- so
the refusal is asserted at one over and the acceptance at exactly the limit.

Every refusal here also makes a second request through the same door that
succeeds. A test asserting only a refusal passes against a route that was
never registered, and seventeen tests in this repo had that defect.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport
from starlette.datastructures import UploadFile

from sro.application.context import RequestContext
from sro.application.observation.policy import SetObservationPolicy
from sro.config import Settings
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import DeviceId, PrincipalId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LENA = DeviceId("dev-lena-laptop")
HERS = "the-secret-lena-s-browser-was-minted"
CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

BELTS = Settings()
"""The shipped defaults, read once. Not literals: a route answering a number
this class does not hold is a belt nobody can loosen for a deployment."""


def _gesture(index: int) -> dict[str, Any]:
    return {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "at": 1772355630.0 + index,
            "url": "https://wms.acme.com/orders",
            "target": {"tag": "button", "cssPath": "div > button"},
        },
    }


def _batch(batch_id: str, events: int) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "device_id": LENA.value,
        "started_at": "2026-03-01T09:00:00Z",
        "ended_at": "2026-03-01T09:01:00Z",
        "mode": "passive",
        "events": [_gesture(i) for i in range(events)],
    }


@pytest.fixture
async def uow() -> AsyncIterator[FakeUnitOfWork]:
    unit = FakeUnitOfWork()
    unit.devices.rows[LENA.value] = AgentDevice(  # type: ignore[attr-defined]
        id=LENA,
        tenant_id=f.TENANT,
        principal_id=PrincipalId("lena@acme.test"),
        label="laptop",
        extension_version="0.1.0",
        registered_at=f.at(0),
        last_seen_at=f.at(0),
        secret=HERS,
    )
    await SetObservationPolicy(unit).execute(CTX, policy=ObservationPolicy().enabled())
    yield unit


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    """One container for the whole test, not one per request.

    Built once so a test can look at what the blob store ended up holding --
    which is how "refused *before* anything was written" is asserted at all.
    """
    return _FakeContainer(uow)


@pytest.fixture
async def client(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={
            "Authorization": f"Bearer {token_for()}",
            "X-Device-Secret": HERS,
        },
    ) as http:
        yield http


async def test_a_batch_one_event_over_the_limit_is_refused(client: httpx.AsyncClient) -> None:
    """Exactly one over, not ten thousand: `>` and `>=` differ by one event and
    a test at 10x the limit passes under both.

    The detail names the count that would have been taken, so a sender that is
    too eager can split rather than guess. And a small batch goes through the
    same door afterwards: `413` from a route nobody registered is impossible,
    but a suite that only ever sees a refusal cannot tell that from a door that
    refuses everything.
    """
    over = BELTS.observation_batch_events + 1

    refused = await client.post("/v1/observations", json=_batch("bat-over", over))
    served = await client.post("/v1/observations", json=_batch("bat-small", 2))

    assert refused.status_code == 413
    assert refused.headers["content-type"].startswith("application/problem+json")
    assert refused.json()["detail"] == (
        f"{over} events in one batch; at most {BELTS.observation_batch_events}"
    )
    assert refused.json()["type"].endswith("/content_too_large")
    # And the title, not only the slug. `_TITLES` renders through
    # `.get(code, "Error")`, so with the slug pinned and the title not, the 413
    # entry could be deleted -- or set to "Bananas" -- and every suite stayed
    # green while the door answered the "Error" title that `fbd2160` was
    # written to remove. `test_refusals.py` already asserts both halves for 429.
    assert refused.json()["title"] == "Content too large"
    assert served.status_code == 202, served.text


async def test_a_batch_exactly_at_the_limit_is_accepted(client: httpx.AsyncClient) -> None:
    """The other side of the same boundary. Without it, `>=` passes the test
    above and silently costs every caller one event."""
    at = BELTS.observation_batch_events

    response = await client.post("/v1/observations", json=_batch("bat-at", at))

    assert response.status_code == 202, response.text
    assert response.json()["accepted"] == at


async def test_an_oversized_artifact_is_refused_without_the_whole_file_in_memory(
    client: httpx.AsyncClient, container: _FakeContainer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `+ 1` read is the decision this test exists to protect.

    `await file.read()` followed by a length check answers the same 413 and is
    the defect: the process has already held every byte the caller chose to
    send in order to say the file was too big. So what is asserted is how many
    bytes the route actually took -- one past the bound and not one more --
    rather than only the status.

    What this does *not* claim: python-multipart has already consumed the
    request body into a spooled file before the route runs. The belt bounds
    what this process holds in memory and hands to the blob store; bounding the
    bytes on the wire is middleware neither this system nor the rig has.

    And the store is checked as well as the answer. A belt applied after the
    upload has been handed on answers the same 413 while the bytes are already
    written, which is the disk this exists to protect.
    """
    read = UploadFile.read
    taken: list[int] = []

    async def counted(self: UploadFile, size: int = -1) -> bytes:
        data = await read(self, size)
        taken.append(len(data))
        return data

    monkeypatch.setattr(UploadFile, "read", counted)

    refused = await client.post(
        "/v1/observations/artifacts",
        data={"device_id": LENA.value, "batch_id": "bat-1", "kind": "screenshot"},
        files={"file": ("shot.png", b"x" * 9_000_000, "image/png")},
    )
    stored_after_the_refusal = dict(container.blobs.objects)
    served = await client.post(
        "/v1/observations/artifacts",
        data={"device_id": LENA.value, "batch_id": "bat-1", "kind": "screenshot"},
        files={"file": ("shot.png", b"a picture", "image/png")},
    )

    assert refused.status_code == 413
    assert refused.json()["detail"] == (
        f"an artifact is at most {BELTS.observation_artifact_bytes} bytes"
    )
    assert taken[0] == BELTS.observation_artifact_bytes + 1
    assert stored_after_the_refusal == {}
    assert served.status_code == 201, served.text
    assert list(container.blobs.objects.values()) == [b"a picture"]


async def test_the_belts_are_the_deployment_s_and_not_the_route_s(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    """Both numbers read from `Settings`, so a deployment can move them.

    A route holding the shipped default as a literal answers every one of the
    tests above, and the operator who needs a wider batch for one warehouse has
    nowhere to say so. Set two absurd belts and watch both doors move: only the
    bound changes, the words and the status do not.
    """
    container.settings = Settings(observation_batch_events=3, observation_artifact_bytes=16)

    batch = await client.post("/v1/observations", json=_batch("bat-tight", 4))
    artifact = await client.post(
        "/v1/observations/artifacts",
        data={"device_id": LENA.value, "batch_id": "bat-1", "kind": "screenshot"},
        files={"file": ("shot.png", b"seventeen bytes!!", "image/png")},
    )
    served = await client.post("/v1/observations", json=_batch("bat-three", 3))

    assert batch.status_code == 413
    assert batch.json()["detail"] == "4 events in one batch; at most 3"
    assert artifact.status_code == 413
    assert artifact.json()["detail"] == "an artifact is at most 16 bytes"
    assert served.status_code == 202, served.text
