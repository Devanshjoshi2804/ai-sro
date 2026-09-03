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


def test_a_truncated_body_does_not_poison_the_batch_id(client: TestClient, store: Store) -> None:
    """It used to answer 202 and take the id, so the real retry was discarded
    as "already had it" and seven gestures vanished with no error anywhere."""
    truncated = {key: value for key, value in BATCH.items() if key != "events"}

    first = client.post("/v1/observations", json=truncated, headers=_auth())

    assert first.status_code == 422

    retry = client.post("/v1/observations", json=BATCH, headers=_auth())

    assert retry.status_code == 202
    assert retry.json()["accepted"] == 7
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_events_of_the_wrong_type_is_a_malformed_envelope(client: TestClient) -> None:
    for events in ("not a list", {"a": "dict"}, 7, None):
        raw = {**BATCH, "events": events}

        response = client.post("/v1/observations", json=raw, headers=_auth())

        assert response.status_code == 422, events


def test_an_artifact_cannot_be_written_outside_the_artifacts_directory(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/observations/artifacts",
        headers=_auth(),
        data={"batch_id": "../../escaped", "kind": "screenshot"},
        files={"file": ("s.png", b"PNG", "image/png")},
    )

    assert response.status_code == 400


def test_the_rejected_count_is_written_down_not_only_returned(
    client: TestClient, store: Store
) -> None:
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

    client.post("/v1/observations", json=raw, headers=_auth())

    row = store.query("SELECT accepted, rejected FROM batches")[0]

    assert row["accepted"] == 7
    assert row["rejected"] == 1


async def test_two_readings_of_the_same_gestures_do_not_both_run(store: Store) -> None:
    """Both callers used to select the same unread rows and bill the model
    twice for each, while INSERT OR REPLACE kept only one cost row."""
    import asyncio

    save_batch(store, Batch.model_validate(BATCH), "new")
    asker = FakeAsker(*[_ok() for _ in range(14)])

    first, second = await asyncio.gather(
        read_new_gestures(store, asker, "gemini-3.8-flash"),
        read_new_gestures(store, asker, "gemini-3.8-flash"),
    )

    assert first + second == 7
    assert store.query("SELECT count(*) AS n FROM intents")[0]["n"] == 7
    assert len(asker.asked) == 7


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


def test_the_streams_route_names_each_browser(client: TestClient) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())

    body = client.get("/v1/streams", headers=_auth()).json()

    assert body["streams"][0]["stream_id"] == "dev_browsertest"
    assert body["streams"][0]["gestures"] == 7


def test_the_gestures_route_pairs_each_gesture_with_its_reading(
    client: TestClient, store: Store
) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())
    row = store.query("SELECT id, tenant FROM gestures ORDER BY at LIMIT 1")[0]
    from rig.api import save_intent
    from rig.records import Intent

    save_intent(store, Intent(gesture_id=row["id"], tenant=row["tenant"], act="typed a code"))

    body = client.get("/v1/gestures?stream=dev_browsertest", headers=_auth()).json()

    assert len(body["gestures"]) == 7
    assert body["gestures"][0]["intent"]["act"] == "typed a code"
    assert body["gestures"][1]["intent"] is None


def test_the_spend_route_adds_up_what_the_readings_cost(client: TestClient, store: Store) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())
    from rig.api import save_intent
    from rig.records import Intent

    for row in store.query("SELECT id, tenant FROM gestures"):
        save_intent(
            store,
            Intent(
                gesture_id=row["id"],
                tenant=row["tenant"],
                act="x",
                in_tokens=400,
                out_tokens=60,
                cost_usd=0.0005,
            ),
        )

    body = client.get("/v1/spend", headers=_auth()).json()

    assert body["gestures_read"] == 7
    assert body["cost_usd"] == pytest.approx(0.0035)
    assert body["in_tokens"] == 2800
    assert body["unpriced"] == 0


def test_the_spend_route_says_how_many_readings_it_could_not_price(
    client: TestClient, store: Store
) -> None:
    """A total that quietly drops the calls it could not price understates the
    bill, which is the whole reason Answer.unpriced exists."""
    client.post("/v1/observations", json=BATCH, headers=_auth())
    from rig.api import save_intent
    from rig.records import Intent

    rows = store.query("SELECT id, tenant FROM gestures")
    for index, row in enumerate(rows):
        save_intent(
            store,
            Intent(
                gesture_id=row["id"],
                tenant=row["tenant"],
                act="x",
                cost_usd=0.0,
                unpriced=index < 2,
            ),
        )

    body = client.get("/v1/spend", headers=_auth()).json()

    assert body["unpriced"] == 2


def test_the_page_is_served(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "rig" in response.text.lower()


def test_a_scroll_does_not_take_the_gestures_route_down(client: TestClient, store: Store) -> None:
    """A scroll carries no target. Calling .get() on that None killed the whole
    route, and real capture is about 15% scrolls."""
    client.post("/v1/observations", json=BATCH, headers=_auth())
    store.execute(
        "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, gesture_json)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            "ges_scroll",
            "new",
            "dev_browsertest",
            BATCH["batch_id"],
            9_999_999_999.0,
            json.dumps({"kind": "scroll", "target": None, "value": "0", "at": 9_999_999_999.0}),
        ),
    )

    response = client.get("/v1/gestures?stream=dev_browsertest", headers=_auth())

    assert response.status_code == 200
    scroll = next(g for g in response.json()["gestures"] if g["id"] == "ges_scroll")
    assert scroll["target"] is None


def test_the_gestures_route_will_not_return_the_whole_table(client: TestClient) -> None:
    """The page polls every three seconds; an unbounded limit is a footgun."""
    client.post("/v1/observations", json=BATCH, headers=_auth())

    response = client.get("/v1/gestures?limit=10000000", headers=_auth())

    assert response.status_code == 200
    assert len(response.json()["gestures"]) <= 1000


def test_the_page_escapes_what_it_draws() -> None:
    """Everything on that page is captured content or a model's words about it.
    A WMS field labelled `<img src=x onerror=...>` must not run there.

    This runs the page's own `line()` in node against hostile input, rather
    than asserting that certain strings appear in the file. A substring check
    would pass with escaping dropped from `why`, `error`, `kind` or the stream
    list -- which is most of the places captured text reaches innerHTML.
    """
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    page = (Path(__file__).parent.parent / "src" / "rig" / "web" / "index.html").read_text()
    script = page.split("<script>")[1].split("</script>")[0]
    # The page's own code, minus the part that talks to the network.
    script = script.split('document.getElementById("stream").addEventListener')[0]

    attack = "<img src=x onerror=alert(1)>"
    harness = (
        # Node has no `location` global; the page's first line reads
        # location.search before line() is ever defined, let alone called.
        "globalThis.location = { search: '' };\n"
        + script
        + f"""
        const g = {{
          kind: {json.dumps(attack)}, calls: 0,
          intent: {{
            act: {json.dumps(attack)}, why: {json.dumps(attack)},
            error: null, cost_usd: 0,
            values_seen: [{{ field: {json.dumps(attack)}, value: {json.dumps(attack)} }}],
          }},
        }};
        const bad = {{ ...g, intent: {{ ...g.intent, act: null, error: {json.dumps(attack)} }} }};
        console.log(line(g) + line(bad));
        """
    )

    out = subprocess.run(
        [node, "--input-type=module", "-e", harness],
        capture_output=True,
        text=True,
        check=False,
    )

    assert out.returncode == 0, out.stderr
    assert "<img src=x" not in out.stdout, "captured text reached the page unescaped"
    assert "&lt;img src=x onerror=alert(1)&gt;" in out.stdout
