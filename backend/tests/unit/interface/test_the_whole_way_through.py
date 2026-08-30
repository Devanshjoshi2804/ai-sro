"""Teach, ask, run — through the front door, over the seams.

Every part of this had tests. Retrieval was still broken on plurals, a count
still came back from a metadata endpoint, and a parameter was still named after
a DOM label the extractor refused to fill in. Each of those lived in a seam
between two well-tested parts, and a suite of 390 green unit tests said nothing
about any of them.

So this walks the path an operator walks, in one test, against fakes for the
world but the real use cases in between: two demonstrations arrive, induction
turns them into a skill, a sentence finds it, and running it sends the call the
demonstration proved. It is deliberately end to end and deliberately shallow --
the point is that the wiring holds, not that any one part is correct.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


SUPPLIERS = "https://wms.test/data/WM/wm/suppliers"

OBJECTIVE = ObjectiveKey(
    objective_type="create",
    target_system="blue_yonder",
    entity_type="supplier",
    facility="SG",
    direction=Direction.INTERNAL,
)


def _demonstration(recording_id: str, supplier: str) -> Any:
    """Somebody opening the supplier screen and creating one.

    The list the screen fetches on the way in is what makes "how many suppliers
    are there" answerable without anybody teaching it.
    """
    listing = f.frame(
        index=0,
        action=InputAction(
            kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Suppliers")
        ),
        requests=(
            f.request(
                method="GET",
                url=f"{SUPPLIERS}?siteId=SG",
                status=200,
                response_body=Body(
                    text=json.dumps({"data": [{"supplierNumber": "EXISTING", "clientId": "C1"}]})
                ),
            ),
        ),
    )
    typing = f.frame(
        index=1,
        action=InputAction(
            kind=ActionKind.TYPE,
            target=f.fingerprint(accessible_name="Supplier"),
            value=supplier,
        ),
        requests=(),
    )
    save = f.frame(
        index=2,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="POST",
                url=f"{SUPPLIERS}?siteId=SG",
                status=201,
                request_body=Body(text=json.dumps({"supplierNumber": supplier, "clientId": "C1"})),
                response_body=Body(text=json.dumps({"data": {"supplierNumber": supplier}})),
            ),
        ),
    )
    recording = f.recording(frames=0, id=f.RecordingId(recording_id), objective_key=OBJECTIVE)
    for frame in (listing, typing, save):
        recording.append_frame(frame)
    recording.seal(f.at(300))
    return recording


@pytest.fixture
async def taught(
    uow: FakeUnitOfWork, container: _FakeContainer
) -> AsyncIterator[httpx.AsyncClient]:
    await uow.recordings.add(_demonstration("rec-a", "SUPPLIER-A"))
    await uow.recordings.add(_demonstration("rec-b", "SUPPLIER-B"))

    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as client:
        yield client


async def _connected(container: _FakeContainer) -> None:
    """What signing in once leaves behind: live values for the headers the
    demonstration sent, scoped to the system and site it was taught against."""
    container.http.unreachable = False
    scope = f"{f.TENANT.value}/blue_yonder/SG"
    await container.vault.store(f"{scope}/authorization", "Bearer live-session")
    await container.vault.store(f"{scope}/x-csrf-token", "live-csrf")
    await container.vault.store(f"{f.TENANT.value}/blue_yonder/cookie", "REFSSessionID=live")


class TestTeachAskRun:
    async def test_two_demonstrations_become_a_skill_somebody_can_ask_for(
        self, taught: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        induced = await taught.post(
            "/v1/skills/induct",
            json={"first_recording_id": "rec-a", "second_recording_id": "rec-b"},
        )
        assert induced.status_code == 201, induced.text
        skill_id = induced.json()["skill_id"]

        # The value that differed between the runs is what the operator is
        # asked for, and it is named after the payload rather than the screen.
        detail = (await taught.get(f"/v1/skills/{skill_id}")).json()
        inputs = [p["name"] for p in detail["versions"][-1]["parameters"] if p["kind"] == "input"]
        assert inputs == ["supplier_number"]

        # And the write it proved is the one it will send.
        plans = [
            step["network_plan"] for step in detail["versions"][-1]["steps"] if step["network_plan"]
        ]
        assert any(plan["method"] == "POST" for plan in plans)

    async def test_the_reading_the_screen_did_is_a_skill_nobody_had_to_teach(
        self, taught: httpx.AsyncClient
    ) -> None:
        """Opening the screen listed the suppliers. That answers a question."""
        await taught.post(
            "/v1/skills/induct",
            json={"first_recording_id": "rec-a", "second_recording_id": "rec-b"},
        )

        names = [skill["name"] for skill in (await taught.get("/v1/skills")).json()]

        assert any("supplier" in name.lower() for name in names)

    async def test_a_run_sends_the_call_the_demonstration_proved(
        self, taught: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        induced = await taught.post(
            "/v1/skills/induct",
            json={"first_recording_id": "rec-a", "second_recording_id": "rec-b"},
        )
        skill_id = induced.json()["skill_id"]
        # A connected system: the session headers the demonstration needed are
        # in the vault, which is what "connect once" leaves behind.
        await _connected(container)
        container.http.answer(status_code=200, text=json.dumps({"data": []}))
        container.http.answer(status_code=201, text=json.dumps({"data": {"supplierNumber": "NEW"}}))

        run = await taught.post(
            f"/v1/skills/{skill_id}/runs",
            json={"parameters": {"supplier_number": "NEW"}, "medium": "network"},
        )

        assert run.status_code == 201, run.text
        outcome = run.json()
        performed = [
            step
            for step in outcome["steps"]
            if step["disposition"] in {"performed", "withheld"} and step["method"]
        ]
        assert performed, f"nothing was attempted: {outcome['steps']}"
        # The write is produced but not sent at this rung, which is the whole
        # point of shadow: an operator can read the request before it is real.
        assert any(step["method"] == "POST" for step in performed)

    async def test_a_run_in_your_own_browser_answers_before_it_finishes(
        self, taught: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        """The id has to arrive while there is still something to watch.

        A device run used to be performed inside the request and returned when
        the last step landed, so `/runs/{id}/stream` had nothing to subscribe to
        until there was nothing left to see. The row now exists, and says it is
        running, before the caller is answered.
        """
        induced = await taught.post(
            "/v1/skills/induct",
            json={"first_recording_id": "rec-a", "second_recording_id": "rec-b"},
        )
        skill_id = induced.json()["skill_id"]
        await _connected(container)

        run = await taught.post(
            f"/v1/skills/{skill_id}/runs",
            json={
                "parameters": {"supplier_number": "NEW"},
                "medium": "network",
                "device_id": "dev-1",
            },
        )

        assert run.status_code == 201, run.text
        answered = run.json()
        assert answered["id"]
        assert answered["status"] == "running"
        # And the row it names is readable straight away, which is the whole
        # point: the console asks for it the moment it is told the id.
        assert (await taught.get(f"/v1/runs/{answered['id']}")).status_code == 200

    async def test_a_write_run_records_the_caller_rather_than_a_typed_name(
        self, taught: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        """Confirming is the operator's to give; who they are is not."""
        induced = await taught.post(
            "/v1/skills/induct",
            json={"first_recording_id": "rec-a", "second_recording_id": "rec-b"},
        )
        skill_id = induced.json()["skill_id"]
        await _connected(container)
        for _ in range(4):
            container.http.answer(status_code=200, text=json.dumps({"data": []}))

        run = await taught.post(
            f"/v1/skills/{skill_id}/runs",
            json={
                "parameters": {"supplier_number": "NEW"},
                "medium": "network",
                "authorized_by": "somebody-else-entirely",
            },
        )

        assert run.json()["authorized_by"] in (None, f.OPERATOR.value)
        assert run.json()["authorized_by"] != "somebody-else-entirely"
