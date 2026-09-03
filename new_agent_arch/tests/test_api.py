import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rig.api import build_app, read_new_gestures, save_batch
from rig.models import Answer, FakeAsker
from rig.store import Store
from rig.wire import Batch
from tests.fixtures import BATCH

TOKEN = "test-token"


@pytest.fixture
def store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


@pytest.fixture
def client(store: Store) -> TestClient:
    return TestClient(
        build_app(
            store=store,
            asker=FakeAsker(),
            token=TOKEN,
            tenant="new",
            read_on_ingest=False,
        )
    )


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_one_unparseable_event_does_not_cost_the_batch(client: TestClient, store: Store) -> None:
    """The protocol: "A rejected event does not reject the batch."""
    raw = json.loads(json.dumps(BATCH))
    raw["events"].append(
        {
            "kind": "gesture",
            "gesture": {
                "kind": "drag",
                "target": {"tag": "div", "cssPath": "div#x"},
                "at": 1.0,
                "url": "https://wms.example/",
            },
            "tab_id": 1,
        }
    )

    response = client.post("/v1/observations", json=raw, headers=_auth())

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == 7
    assert body["rejected"] == 1
    assert body["problems"][0]["index"] == len(BATCH["events"])
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_a_batch_is_accepted_and_its_gestures_are_stored(client: TestClient, store: Store) -> None:
    response = client.post("/v1/observations", json=BATCH, headers=_auth())

    assert response.status_code == 202
    assert response.json()["accepted"] == 7
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_the_same_batch_twice_stores_one_copy(client: TestClient, store: Store) -> None:
    """Idempotent on batch_id: the extension retries, and must not double-count."""
    client.post("/v1/observations", json=BATCH, headers=_auth())
    again = client.post("/v1/observations", json=BATCH, headers=_auth())

    assert again.status_code == 202
    assert again.json()["already_had_it"] is True
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_no_page_event_is_lost(client: TestClient, store: Store) -> None:
    """Both page events in the fixture precede the first gesture. A page always
    loads before the operator acts on it, so losing those loses every navigation."""
    client.post("/v1/observations", json=BATCH, headers=_auth())

    attached = sum(
        len(json.loads(row["page_events"]))
        for row in store.query("SELECT page_events FROM gestures")
    )
    orphaned = store.query("SELECT count(*) AS n FROM orphan_pages")[0]["n"]

    assert attached + orphaned == 2
    assert attached == 2


def test_an_orphan_call_is_kept(client: TestClient, store: Store) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())

    stored = store.query("SELECT count(*) AS n FROM orphan_requests")[0]["n"]
    owned = sum(
        len(json.loads(row["requests"])) for row in store.query("SELECT requests FROM gestures")
    )

    assert stored + owned == 5


def test_a_credential_value_is_nowhere_on_disk(
    client: TestClient, store: Store, tmp_path: Path
) -> None:
    """WAL mode keeps recent writes in rig.db-wal, so reading rig.db alone
    would pass this test without proving anything."""
    loud = json.loads(json.dumps(BATCH))
    for event in loud["events"]:
        if event["kind"] == "gesture" and event["gesture"].get("secret"):
            event["gesture"]["value"] = "hunter2"

    client.post("/v1/observations", json=loud, headers=_auth())

    written = b"".join(path.read_bytes() for path in tmp_path.glob("rig.db*")).decode("latin-1")

    assert "rig.db" in str(list(tmp_path.glob("rig.db*")))  # the files exist
    assert "hunter2" not in written


def test_a_malformed_envelope_is_refused_with_422_not_500(client: TestClient) -> None:
    """A bad event is tolerated. A bad batch is not, and says so usefully."""
    headless = {key: value for key, value in BATCH.items() if key != "batch_id"}

    response = client.post("/v1/observations", json=headless, headers=_auth())

    assert response.status_code == 422


def test_no_token_is_refused(client: TestClient) -> None:
    assert client.post("/v1/observations", json=BATCH).status_code == 401


def test_a_wrong_token_is_refused(client: TestClient) -> None:
    response = client.post("/v1/observations", json=BATCH, headers={"Authorization": "Bearer nope"})

    assert response.status_code == 401


async def test_every_stored_gesture_gets_read_once(store: Store) -> None:
    save_batch(store, Batch.model_validate(BATCH), "new")
    asker = FakeAsker(*[_ok() for _ in range(7)])

    written = await read_new_gestures(store, asker, "gemini-3.8-flash")

    assert written == 7
    assert store.query("SELECT count(*) AS n FROM intents")[0]["n"] == 7

    again = await read_new_gestures(store, asker, "gemini-3.8-flash")

    assert again == 0


async def test_a_reading_that_failed_is_still_written(store: Store) -> None:
    """Otherwise the loop retries it forever and the bill never stops."""
    save_batch(store, Batch.model_validate(BATCH), "new")
    asker = FakeAsker(*[Answer(error="503") for _ in range(7)])

    await read_new_gestures(store, asker, "gemini-3.8-flash")

    rows = store.query("SELECT error FROM intents")
    assert len(rows) == 7
    assert all(row["error"] == "503" for row in rows)


def _ok() -> Answer:
    return Answer(
        data={"act": "did a thing", "why": "because", "confidence": "high"},
        in_tokens=400,
        out_tokens=60,
        cost_usd=0.0005,
    )
