import asyncio
import json
import logging
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from rig.api import _read_unread, _row_to_gesture, build_app, read_new_gestures, save_batch
from rig.models import Answer, Effort, FakeAsker
from rig.store import Store
from rig.wire import Batch
from rig.workflows import Step, Workflow, save_workflow
from tests.fixtures import BATCH, SNAPSHOT

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


def _seed_workflow(store: Store) -> Workflow:
    """The fixture workflow, under this file's tenant.

    The body is `tests/test_shapes.py::_workflow`; the two files are allowed to
    repeat it rather than one importing the other's private helper.
    """
    save_batch(store, Batch.model_validate(BATCH), "new")
    ids = [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]
    # `gesture_json` is pydantic's own compact dump, so a substring probe for
    # `"kind": "type"` never matches. Read the column rather than grep it.
    typed = next(
        r["id"]
        for r in store.query("SELECT id, gesture_json FROM gestures ORDER BY at")
        if json.loads(r["gesture_json"]).get("kind") == "type"
        and json.loads(r["gesture_json"]).get("value") == "ACME-4471"
    )
    workflow = Workflow(
        id="wfl_1",
        tenant="new",
        title="create a client",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(
                order=0,
                says="type the code",
                system=None,
                cites=[typed],
                parameters=["clientCode"],
            ),
            Step(order=1, says="save", system=None, cites=[ids[-1]]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["ACME-4471"]}],
    )
    save_workflow(store, workflow)
    return workflow


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


def test_a_batch_of_snapshots_says_so_instead_of_reading_empty(
    client: TestClient, store: Store
) -> None:
    """A batch of only snapshot events used to answer accepted: 0, rejected: 0
    -- indistinguishable from an empty batch. snapshots_ignored is the count
    that tells the caller something did arrive."""
    raw = json.loads(json.dumps(BATCH))
    raw["events"] = [SNAPSHOT, SNAPSHOT]

    response = client.post("/v1/observations", json=raw, headers=_auth())

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == 0
    assert body["rejected"] == 0
    assert body["snapshots_ignored"] == 2


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


# Every route the audit proved carried a credential to disk, one distinctive
# value each so a failure names the field that leaked rather than saying
# something did. The test that used to plant only the first of these stayed
# green while the other nine leaked in the same harness.
PLANTED = {
    "gesture.value": "hunter2GestureValue",
    "gesture.url fragment": "hunter2GestureUrl",
    "GestureEvent.frame_url": "hunter2FrameUrl",
    "Request.url query": "hunter2RequestUrl",
    "Request.request_headers": "hunter2RequestHeader",
    "Request.request_body.text": "hunter2RequestBody",
    "Request.response_body.text": "hunter2ResponseBody",
    "Request.redirect_chain[0].url": "hunter2HopUrl",
    "Request.redirect_chain[0].headers": "hunter2HopHeader",
    "PageEvent.url": "hunter2PageUrl",
    "PageEvent.detail": "hunter2PageDetail",
}


def _loud(batch: dict[str, Any]) -> dict[str, Any]:
    """The fixture with a credential on every one of those routes."""
    loud = json.loads(json.dumps(batch))
    for event in loud["events"]:
        if event["kind"] == "gesture":
            gesture = event["gesture"]
            if gesture.get("secret") or (gesture.get("target") or {}).get("secret"):
                gesture["value"] = PLANTED["gesture.value"]
            # OAuth implicit flow hands a token back in the fragment.
            gesture["url"] = (
                f"https://wms.example/app#access_token={PLANTED['gesture.url fragment']}"
            )
            event["frame_url"] = (
                f"https://wms.example/app?api_key={PLANTED['GestureEvent.frame_url']}"
            )
        elif event["kind"] == "request":
            request = event["request"]
            joiner = "&" if "?" in request["url"] else "?"
            request["url"] += f"{joiner}session_token={PLANTED['Request.url query']}"
            request["request_headers"]["Authorization"] = (
                f"Bearer {PLANTED['Request.request_headers']}"
            )
            # Nested, because the flat rule guarded only the top level.
            request["request_body"] = {
                "text": json.dumps({"auth": {"password": PLANTED["Request.request_body.text"]}}),
                "mime_type": "application/json",
            }
            # A SOAP login: the shape the audit traced all the way to the page.
            request["response_body"] = {
                "text": f"<Login><password>{PLANTED['Request.response_body.text']}</password></Login>",
                "mime_type": "text/xml",
            }
            request["redirect_chain"] = [
                {
                    "url": f"https://sso.example/cb?access_token={PLANTED['Request.redirect_chain[0].url']}",
                    "status": 302,
                    "headers": {
                        "Authorization": f"Bearer {PLANTED['Request.redirect_chain[0].headers']}"
                    },
                }
            ]
        elif event["kind"] == "page":
            event["url"] = f"https://wms.example/in?magic_link_token={PLANTED['PageEvent.url']}"
            event["detail"] = f"password={PLANTED['PageEvent.detail']}"
    return loud


def test_a_credential_value_is_nowhere_on_disk(
    client: TestClient, store: Store, tmp_path: Path
) -> None:
    """WAL mode keeps recent writes in rig.db-wal, so reading rig.db alone
    would pass this test without proving anything."""
    client.post("/v1/observations", json=_loud(BATCH), headers=_auth())

    written = b"".join(path.read_bytes() for path in tmp_path.glob("rig.db*")).decode("latin-1")

    assert "rig.db" in str(list(tmp_path.glob("rig.db*")))  # the files exist
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7  # and hold the batch
    for route, credential in PLANTED.items():
        assert credential not in written, route


class _QuotingAsker:
    """A model that quotes its evidence back, which is what the audit's did.

    `values_seen` is guarded at the write point; `why`, `act` and `object` are
    model prose and can repeat anything the prompt contained. So the only thing
    that keeps a credential out of `why` is it never being in the prompt.
    """

    def __init__(self) -> None:
        self.asked: list[dict[str, Any]] = []

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
        effort: Effort | None = None,
    ) -> Answer:
        await asyncio.sleep(0)
        self.asked.append({"evidence": evidence})
        return Answer(data={"act": "logged in", "why": evidence}, in_tokens=1, out_tokens=1)


async def test_an_xml_login_body_reaches_neither_the_prompt_nor_the_page(
    client: TestClient, store: Store
) -> None:
    """The end-to-end route the audit traced: a SOAP login body, a model that
    quotes its evidence into `why`, and `GET /v1/gestures`, which index.html
    renders."""
    loud = json.loads(json.dumps(BATCH))
    for event in loud["events"]:
        if event["kind"] == "request":
            event["request"]["request_body"] = {
                "text": "<Login><user>bob</user><password>hunter2</password></Login>",
                "mime_type": "text/xml",
            }
    client.post("/v1/observations", json=loud, headers=_auth())
    asker = _QuotingAsker()

    await read_new_gestures(store, asker, "gemini-3.8-flash", "new")

    prompts = "".join(asked["evidence"] for asked in asker.asked)
    page = client.get("/v1/gestures", headers=_auth()).text

    assert prompts, "no reading happened, so this proves nothing"
    assert "hunter2" not in prompts
    assert "hunter2" not in page
    # The word, not the guillemets: the evidence is json.dumps'd with the
    # default ensure_ascii, so what reaches the page is « escaped as \u00ab.
    assert "redacted" in page  # the marker is what says a credential was there


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
        read_new_gestures(store, asker, "gemini-3.8-flash", "new"),
        read_new_gestures(store, asker, "gemini-3.8-flash", "new"),
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

    written = await read_new_gestures(store, asker, "gemini-3.8-flash", "new")

    assert written == 7
    assert store.query("SELECT count(*) AS n FROM intents")[0]["n"] == 7

    again = await read_new_gestures(store, asker, "gemini-3.8-flash", "new")

    assert again == 0


async def test_the_reading_is_told_about_the_calls_the_gesture_caused(store: Store) -> None:
    """correlate exists to attach calls to a gesture and trim exists to show
    them to the model. For a while neither reached it: _row_to_gesture dropped
    both columns, and every reading was made from the gesture alone."""
    save_batch(store, Batch.model_validate(BATCH), "new")
    asker = FakeAsker(*[_ok() for _ in range(10)])

    await read_new_gestures(store, asker, "gemini-3.8-flash", "new")

    prompts = [asked["evidence"] for asked in asker.asked]
    with_calls = [p for p in prompts if '"calls": []' not in p and '"calls"' in p]

    assert with_calls, "no reading was shown a single network call"


def test_a_gesture_read_back_still_carries_its_evidence(store: Store) -> None:
    save_batch(store, Batch.model_validate(BATCH), "new")
    row = store.query("SELECT * FROM gestures WHERE json_array_length(requests) > 0 LIMIT 1")[0]

    gesture = _row_to_gesture(row)

    assert len(gesture.requests) == len(json.loads(row["requests"]))
    assert gesture.requests[0].method


async def test_a_reading_that_failed_is_still_written(store: Store) -> None:
    """Otherwise the loop retries it forever and the bill never stops."""
    save_batch(store, Batch.model_validate(BATCH), "new")
    asker = FakeAsker(*[Answer(error="503") for _ in range(7)])

    await read_new_gestures(store, asker, "gemini-3.8-flash", "new")

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


def test_the_gestures_route_will_not_return_the_whole_table(
    client: TestClient, store: Store
) -> None:
    """The page polls every three seconds; an unbounded limit is a footgun.

    Against the 7-gesture fixture this asserted `<= 1000` and passed with the
    clamp deleted -- it could not fail. There have to be more rows than the cap
    for the cap to be visible at all.
    """
    client.post("/v1/observations", json=BATCH, headers=_auth())
    with store.connect() as connection:
        connection.executemany(
            "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, gesture_json)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    f"ges_bulk_{n}",
                    "new",
                    "dev_browsertest",
                    BATCH["batch_id"],
                    1_000_000.0 + n,
                    json.dumps({"kind": "scroll", "target": None, "at": 1_000_000.0 + n}),
                )
                for n in range(1200)
            ],
        )

    response = client.get("/v1/gestures?limit=10000000", headers=_auth())

    assert response.status_code == 200
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 1207
    assert len(response.json()["gestures"]) == 1000


def test_the_page_escapes_what_it_draws() -> None:
    """Everything on that page is captured content or a model's words about it.
    A WMS field labelled `<img src=x onerror=...>` must not run there.

    This runs the page's own `line()` in node against hostile input, rather
    than asserting that certain strings appear in the file. A substring check
    would pass with escaping dropped from `why`, `error`, `kind` or the stream
    list -- which is most of the places captured text reaches innerHTML.
    """
    attack = "<img src=x onerror=alert(1)>"
    out = _run_page(
        f"""
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

    assert "<img src=x" not in out, "captured text reached the page unescaped"
    assert "&lt;img src=x onerror=alert(1)&gt;" in out


def test_an_artifact_cannot_be_written_outside_by_its_kind_either(
    client: TestClient, tmp_path: Path
) -> None:
    """batch_id was checked and `kind` was not, though both are form fields and
    both go into the path. The sibling answered 201 and wrote the bytes."""
    escape = tmp_path / "escaped"

    answer = client.post(
        "/v1/observations/artifacts",
        data={"batch_id": "bat_1", "kind": "../" * 12 + str(escape).lstrip("/")},
        files={"file": ("s.png", b"PWNED", "image/png")},
        headers=_auth(),
    )

    assert answer.status_code == 400
    assert not escape.with_name("escaped-x.png").exists()


# --- Finding 1: one bad timestamp must cost one event, not the batch ----------


def _with(events: list[dict[str, Any]], batch_id: str) -> dict[str, Any]:
    raw = json.loads(json.dumps(BATCH))
    raw["batch_id"] = batch_id
    raw["events"].extend(events)
    return raw


def test_one_unreadable_timestamp_does_not_cost_the_batch(client: TestClient, store: Store) -> None:
    """Proved by the audit: started_at='not-a-time' answered HTTP 500 and stored
    nothing at all -- seven good gestures lost to one bad field, and a 500 is
    not a permanent 4xx, so the extension retries that batch forever while the
    device's capture stalls with nothing saying so."""

    def first_of(kind: str) -> dict[str, Any]:
        events = json.loads(json.dumps(BATCH["events"]))
        return next(event for event in events if event["kind"] == kind)

    bad_request = first_of("request")
    bad_request["request"]["request_id"] = "r_broken"
    bad_request["request"]["started_at"] = "not-a-time"

    bad_page = first_of("page")
    bad_page["at"] = "2026-09-04 10:00:00 IST"

    bad_gesture = first_of("gesture")
    bad_gesture["gesture"]["at"] = "not-a-time"

    for name, event, field in (
        ("request.started_at", bad_request, "started_at"),
        ("page.at", bad_page, "at"),
        ("gesture.at", bad_gesture, "at"),
    ):
        response = client.post(
            "/v1/observations", json=_with([event], f"bat_{field}_{name}"), headers=_auth()
        )

        assert response.status_code == 202, name
        body = response.json()
        assert body["accepted"] == 7, name
        assert body["rejected"] == 1, name
        assert body["problems"][0]["index"] == len(BATCH["events"]), name
        where = body["problems"][0]["reason"].split(":", 1)[0]
        assert where.endswith(field), (name, body["problems"])

    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 21


# --- Finding 2: a reading that produced nothing usable ------------------------


def _unusable() -> Answer:
    """What the audit's model did: an `act` of the wrong type, which
    intents._string_field correctly nulls -- after the call was billed."""
    return Answer(
        data={"act": ["a", "list"], "why": "it looked like a pick"},
        in_tokens=400,
        out_tokens=60,
        cost_usd=0.0037,
    )


async def test_a_billed_reading_with_no_act_is_neither_hidden_nor_billed_twice(
    client: TestClient, store: Store
) -> None:
    """$0.0259 spent, seven intent rows written, and /v1/gestures served three
    of them as null so the console said "not read yet" while /v1/spend said
    seven were read. The two routes must describe the same rows the same way,
    and the cost must stay where a person can see it."""
    client.post("/v1/observations", json=BATCH, headers=_auth())

    read = await read_new_gestures(store, FakeAsker(*[_unusable() for _ in range(7)]), "m", "new")

    assert read == 7
    spend = client.get("/v1/spend", headers=_auth()).json()
    served = client.get("/v1/gestures?stream=dev_browsertest", headers=_auth()).json()["gestures"]
    with_intent = [g for g in served if g["intent"] is not None]

    # The two routes agree about which rows were read.
    assert spend["gestures_read"] == len(with_intent) == 7
    # And say plainly that none of those readings produced anything usable.
    assert spend["unusable"] == 7
    assert spend["cost_usd"] == pytest.approx(0.0259)
    # The cost of each is visible rather than dropped with the row.
    assert all(g["intent"]["act"] is None for g in with_intent)
    assert all(g["intent"]["cost_usd"] == pytest.approx(0.0037) for g in with_intent)
    assert all(g["intent"]["why"] for g in with_intent)

    # Billed once. A row that was asked and answered is not asked again.
    asker = FakeAsker(*[_ok() for _ in range(7)])
    assert await read_new_gestures(store, asker, "m", "new") == 0
    assert asker.asked == []


# --- Finding 3: the reading loop must not fail in silence ---------------------


async def test_a_reading_loop_that_dies_says_so(
    store: Store, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """It caught Exception and passed. Nothing else in this system notices: no
    intent rows appear, /v1/spend keeps saying 0 read, and the page looks
    exactly like an operator who has done nothing all morning."""
    from rig import api

    async def explode(*_: Any, **__: Any) -> int:
        raise RuntimeError("the store fell over")

    monkeypatch.setattr(api, "_read_unread", explode)

    with caplog.at_level("ERROR"):
        await api._read_soon(store, FakeAsker(), "new")

    assert caplog.records, "the loop died and said nothing anywhere"
    assert "the store fell over" in caplog.text


async def test_the_reading_task_is_held_until_it_finishes(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """asyncio.create_task's return value is the only strong reference there
    is; the loop keeps a weak one, so a discarded task can be collected
    mid-execution and the reading simply never happens."""
    from rig import api

    running = asyncio.Event()
    finish = asyncio.Event()

    async def slow(*_: Any, **__: Any) -> int:
        running.set()
        await finish.wait()
        return 0

    monkeypatch.setattr(api, "_read_unread", slow)

    task = api._spawn_reading(store, FakeAsker(), "new")
    await running.wait()

    assert task in api._reading_tasks, "nothing holds the running task"

    finish.set()
    await task

    assert task not in api._reading_tasks, "a finished task is never let go of"


# --- Finding 4: unpriced, in the one place a human reads it -------------------


def _browser(href: str = "http://rig.test/") -> str:
    """The browser the page runs in, as much of it as the page's top level uses.

    `location.href` rather than only `location.search`, because the page reads
    the token out of the whole URL and then puts a shortened one back through
    `history.replaceState` -- the point of which is that the credential stops
    being in the address bar. Both `history` and `sessionStorage` record what
    they were given, so a test can read them back.
    """
    return f"""
globalThis.location = {{ href: {json.dumps(href)} }};
globalThis.history = {{
  replaced: [],
  replaceState(_state, _title, url) {{ this.replaced.push(url); }},
}};
globalThis.sessionStorage = {{
  held: new Map(),
  getItem(key) {{ return this.held.has(key) ? this.held.get(key) : null; }},
  setItem(key, value) {{ this.held.set(key, String(value)); }},
}};
"""


def _run_page(tail: str, browser: str | None = None) -> str:
    """The page's own script in node, minus the part that talks to the network.

    Running it beats grepping the file: a substring check passes with escaping
    dropped from `why`, or with the cost cell left blank for an unpriced row.
    """
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    page = (Path(__file__).parent.parent / "src" / "rig" / "web" / "index.html").read_text()
    script = page.split("<script>")[1].split("</script>")[0]
    script = script.split('document.getElementById("stream").addEventListener')[0]
    out = subprocess.run(
        [node, "--input-type=module", "-e", (browser or _browser()) + script + tail],
        capture_output=True,
        text=True,
        check=False,
    )

    assert out.returncode == 0, out.stderr
    return out.stdout


def test_the_page_tells_an_unpriced_reading_from_an_unread_gesture() -> None:
    """`intent?.cost_usd ? ... : ""` drew an unpriced ($0.00) reading with an
    empty cost cell -- byte-identical to a gesture nobody has read. `unpriced`
    exists precisely because those two cannot be told apart by cost_usd alone,
    and the console was the one place it never appeared."""
    rendered = _run_page(
        """
        const base = { kind: "click", calls: 0 };
        const unread = { ...base, intent: null };
        const unpriced = { ...base, intent: { act: "picked", why: "w", cost_usd: 0,
                                              unpriced: true, values_seen: [] } };
        const free = { ...base, intent: { act: "picked", why: "w", cost_usd: 0,
                                          unpriced: false, values_seen: [] } };
        console.log(JSON.stringify([line(unread), line(unpriced), line(free)]));
        """
    )
    unread, unpriced, free = json.loads(rendered)

    assert unread != unpriced, "an unpriced reading looks exactly like an unread gesture"
    assert unpriced != free, "an honestly-unpriced row looks exactly like a $0.00 one"
    assert "unpriced" in unpriced
    assert "$0.00000" in free


def test_the_page_shows_a_reading_that_produced_nothing_usable() -> None:
    """Neither unread nor read. The row must not claim to be either."""
    rendered = _run_page(
        """
        const base = { kind: "click", calls: 0 };
        const unread = { ...base, intent: null };
        const nothing = { ...base, intent: { act: null, error: null, why: "could not tell",
                                             cost_usd: 0.0037, values_seen: [] } };
        console.log(JSON.stringify([line(unread), line(nothing)]));
        """
    )
    unread, nothing = json.loads(rendered)

    assert "not read yet" in unread
    assert "not read yet" not in nothing, "a billed reading is shown as unread"
    assert "$0.00370" in nothing, "the money it cost is not on the page"


def test_the_header_shows_what_the_spend_route_could_not_price() -> None:
    """/v1/spend computes `unpriced`, returns it, and the header dropped it."""
    rendered = _run_page(
        """
        const clean = { gestures: 9, gestures_read: 7, cost_usd: 0.0259,
                        per_gesture_usd: 0.0037, unpriced: 0, unusable: 0 };
        console.log(JSON.stringify([
          spendLine(clean),
          spendLine({ ...clean, unpriced: 2 }),
          spendLine({ ...clean, unusable: 3 }),
        ]));
        """
    )
    clean, unpriced, unusable = json.loads(rendered)

    assert "unpriced" not in clean and "unusable" not in clean
    assert "2" in unpriced and "unpriced" in unpriced
    assert "3" in unusable and "unusable" in unusable
    # The arithmetic divides the bill by readings, so the label says readings.
    assert "a reading" in clean
    assert "a gesture" not in clean


def test_the_header_shows_a_mining_pass_it_could_not_price() -> None:
    """`unpriced`'s sibling one field over. /v1/spend emits `mining_unpriced`
    and the header rendered only `mining_usd`, so a pass on a model missing
    from PRICES drew "$0.0000 mining over 1" -- which is exactly what happened:
    findings.md records mining_usd 0.0 beside mining_unpriced 1 while $1.12 was
    billed. Seventh instance of the sibling-field pattern.
    """
    rendered = _run_page(
        """
        const base = { gestures: 9, gestures_read: 7, cost_usd: 0.0259,
                       per_gesture_usd: 0.0037, unpriced: 0, unusable: 0,
                       passes: 1, mining_usd: 0, mining_unpriced: 0 };
        console.log(JSON.stringify([
          spendLine(base),
          spendLine({ ...base, mining_unpriced: 1 }),
          spendLine({ ...base, passes: 0, mining_unpriced: 1 }),
        ]));
        """
    )
    priced, unpriced, no_pass = json.loads(rendered)

    assert priced != unpriced, "a mining pass nobody could price reads as a free one"
    assert "unpriced" in unpriced
    assert "unpriced" not in priced
    assert "mining" not in no_pass, "no pass ran, so there is no mining line to qualify"


# --- The tail is one operator's own history, and nobody else's ----------------


def _as_device(device_id: str, batch_id: str, shift: float) -> dict[str, Any]:
    """The committed batch, re-badged to another browser and moved in time."""
    raw = json.loads(json.dumps(BATCH))
    raw["batch_id"] = batch_id
    raw["device_id"] = device_id
    for event in raw["events"]:
        if event["kind"] == "gesture":
            event["gesture"]["at"] += shift
    return raw


def _saying(act: str) -> Answer:
    return Answer(data={"act": act, "why": "because"}, in_tokens=1, out_tokens=1)


async def test_one_operators_history_is_never_another_operators_prompt(store: Store) -> None:
    """tail_for's `WHERE g.stream_id = ?`. Two devices in one store, and with
    the filter gone the eight most recent readings before this gesture are
    whoever's -- so alice's morning arrives as context for bob's click and is
    sent to the model as what *he* was just doing. Nothing tested it.
    """
    save_batch(store, Batch.model_validate(_as_device("dev_alice", "bat_alice", 0.0)), "new")
    alice = FakeAsker(*[_saying("alice cancelled order ORD-8841") for _ in range(7)])
    await read_new_gestures(store, alice, "m", "new")
    assert len(alice.asked) == 7

    save_batch(store, Batch.model_validate(_as_device("dev_bob", "bat_bob", 600.0)), "new")
    bob = FakeAsker(*[_saying("bob received tote TOT-12") for _ in range(7)])
    await read_new_gestures(store, bob, "m", "new")

    prompts = "".join(asked["evidence"] for asked in bob.asked)

    assert len(bob.asked) == 7, "bob's gestures were not read, so this proves nothing"
    # The tail reaches the prompt at all -- without this the assertion below
    # passes just as well with `tail=[]` hard-coded.
    assert "bob received tote TOT-12" in prompts
    assert "alice cancelled order ORD-8841" not in prompts


def test_the_tail_is_the_eight_readings_before_this_one_oldest_first(store: Store) -> None:
    """`LIMIT 8` and `reversed()`, neither of which anything reached.

    Newest-first context tells the model the operator did these things in the
    opposite order to the one they did them in, and an unbounded tail sends the
    whole morning to be billed for on every single gesture.
    """
    from rig.api import save_intent, tail_for
    from rig.records import Intent

    for n in range(12):
        store.execute(
            "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, gesture_json)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                f"ges_{n}",
                "new",
                "dev_a",
                "bat_a",
                1000.0 + n,
                json.dumps({"kind": "click", "at": 1000.0 + n}),
            ),
        )
        save_intent(store, Intent(gesture_id=f"ges_{n}", tenant="new", act=f"did {n}"))

    tail = tail_for(store, "dev_a", 1000.0 + 12)

    assert [intent.act for intent in tail] == [f"did {n}" for n in range(4, 12)]


def test_a_timestamp_with_no_timezone_is_refused_where_it_arrives(
    client: TestClient, store: Store
) -> None:
    """The parseable-but-zone-less case, which is worse than the unparseable
    one because nothing raises. `_epoch` calls .timestamp() on a naive
    datetime, which reads it as local time -- so on a +05:30 machine the same
    instant as '...Z' lands 19800s away, every request detaches from its
    gesture, and every gesture is read with no evidence. Silently.
    """
    events = json.loads(json.dumps(BATCH["events"]))
    zoneless = next(event for event in events if event["kind"] == "page")
    zoneless["at"] = "2026-08-31T08:40:04.582"

    response = client.post(
        "/v1/observations", json=_with([zoneless], "bat_zoneless"), headers=_auth()
    )

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == 7  # the good events beside it are kept
    assert body["rejected"] == 1
    assert "no timezone" in body["problems"][0]["reason"]
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_a_batch_already_had_is_not_read_a_second_time(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`read_on_ingest and not already`. The extension retries; a retry that
    spawns a second drain has the reading lock, not idempotence, standing
    between it and asking the model twice for every gesture in the batch."""
    from rig import api

    spawned: list[int] = []
    monkeypatch.setattr(api, "_spawn_reading", lambda *_: spawned.append(1))

    reading = TestClient(
        build_app(store=store, asker=FakeAsker(), token=TOKEN, tenant="new", read_on_ingest=True)
    )
    reading.post("/v1/observations", json=BATCH, headers=_auth())
    reading.post("/v1/observations", json=BATCH, headers=_auth())

    assert spawned == [1], "a re-sent batch spawned a second reading of the same rows"

    quiet = TestClient(
        build_app(store=store, asker=FakeAsker(), token=TOKEN, tenant="new", read_on_ingest=False)
    )
    quiet.post("/v1/observations", json=_with([], "bat_quiet"), headers=_auth())

    assert spawned == [1], "read_on_ingest=False still spawned a reading"


async def test_one_upload_bigger_than_a_page_is_drained_not_left_half_read(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_read_soon's drain loop. read_new_gestures takes at most 200 rows and
    fires once per batch, so the remainder waited for another batch that may
    never come -- when capture stops for the day, those readings never happen.
    The fix shipped with no regression test."""
    from rig import api

    save_batch(store, Batch.model_validate(BATCH), "new")
    with store.connect() as connection:
        connection.executemany(
            "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, gesture_json)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    f"ges_many_{n}",
                    "new",
                    "dev_browsertest",
                    BATCH["batch_id"],
                    2_000_000.0 + n,
                    json.dumps({"kind": "scroll", "target": None, "at": 2_000_000.0 + n}),
                )
                for n in range(450)
            ],
        )

    asker = FakeAsker(*[_ok() for _ in range(457)])
    monkeypatch.setattr(api.settings(), "intent_model", "m", raising=False)
    await api._read_soon(store, asker, "new")

    assert store.query("SELECT count(*) AS n FROM intents")[0]["n"] == 457


def test_the_spend_route_survives_a_rig_that_has_read_nothing(client: TestClient) -> None:
    """`if row["n"] else 0.0`. Dividing the bill by zero readings is a 500 on
    the one route the console polls, on a rig that has just been started."""
    body = client.get("/v1/spend", headers=_auth()).json()

    assert body["gestures"] == 0
    assert body["gestures_read"] == 0
    assert body["per_gesture_usd"] == 0.0


def test_the_spend_route_counts_gestures_nobody_has_read(client: TestClient, store: Store) -> None:
    """`gestures` is its own count, not the intents count. Taking both from
    the intents row says "7/7 read" the moment the first reading lands."""
    from rig.api import save_intent
    from rig.records import Intent

    client.post("/v1/observations", json=BATCH, headers=_auth())
    row = store.query("SELECT id, tenant FROM gestures ORDER BY at LIMIT 1")[0]
    save_intent(store, Intent(gesture_id=row["id"], tenant=row["tenant"], act="x"))

    body = client.get("/v1/spend", headers=_auth()).json()

    assert body["gestures"] == 7
    assert body["gestures_read"] == 1


def test_the_spend_route_does_not_show_the_float_noise(client: TestClient, store: Store) -> None:
    """`round(c, 6)`. Three readings at a tenth of a cent sum to
    0.30000000000000004 in IEEE754, and that is what the header rendered."""
    from rig.api import save_intent
    from rig.records import Intent

    client.post("/v1/observations", json=BATCH, headers=_auth())
    for row in store.query("SELECT id, tenant FROM gestures ORDER BY at LIMIT 3"):
        save_intent(
            store, Intent(gesture_id=row["id"], tenant=row["tenant"], act="x", cost_usd=0.1)
        )

    body = client.get("/v1/spend", headers=_auth()).json()

    assert body["cost_usd"] == 0.3


def test_a_control_named_only_by_its_extjs_label_still_has_a_name(
    client: TestClient, store: Store
) -> None:
    """`_target_name`'s fieldLabel fallback. Half the controls in an ExtJS WMS
    carry no `name` at all -- the label is the only thing that says what the
    operator touched, and without the fallback the page draws a blank cell."""
    client.post("/v1/observations", json=BATCH, headers=_auth())
    for gesture_id, target in (
        ("ges_label_only", {"tag": "input", "component": {"fieldLabel": "Client Code"}}),
        ("ges_named", {"tag": "input", "name": "Dock", "component": {"fieldLabel": "ignored"}}),
    ):
        store.execute(
            "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, gesture_json)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                gesture_id,
                "new",
                "dev_browsertest",
                BATCH["batch_id"],
                3_000_000.0,
                json.dumps({"kind": "click", "target": target, "at": 3_000_000.0}),
            ),
        )

    served = {
        gesture["id"]: gesture["target"]
        for gesture in client.get("/v1/gestures", headers=_auth()).json()["gestures"]
    }

    assert served["ges_label_only"] == "Client Code"
    assert served["ges_named"] == "Dock"  # `name` still wins when there is one


def test_the_same_call_reported_twice_does_not_lose_the_batch(
    client: TestClient, store: Store
) -> None:
    """`INSERT OR IGNORE` on orphan_requests, whose key is (batch_id,
    request_id). The extension re-reports a request across a redirect, and
    without the IGNORE the IntegrityError rolls the whole transaction back --
    seven gestures gone, and the batch_id already claimed."""

    def orphan(request_id: str) -> dict[str, Any]:
        event = json.loads(json.dumps(next(e for e in BATCH["events"] if e["kind"] == "request")))
        event["request"]["request_id"] = request_id
        event["request"]["started_at"] = "2020-01-01T00:00:00Z"  # long before any gesture
        return event

    response = client.post(
        "/v1/observations",
        json=_with([orphan("r_dupe"), orphan("r_dupe")], "bat_dupe_call"),
        headers=_auth(),
    )

    assert response.status_code == 202
    assert response.json()["accepted"] == 7
    assert response.json()["already_had_it"] is False
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7
    kept = store.query(
        "SELECT count(*) AS n FROM orphan_requests WHERE batch_id = ?", ("bat_dupe_call",)
    )[0]["n"]
    assert kept == 1


def test_a_page_event_nobody_owns_is_stored_whole_not_as_a_marker(
    client: TestClient, store: Store
) -> None:
    """orphan_pages.payload. "A background poll is evidence that a background
    poll happened" -- a row that records only that something arrived, without
    what arrived, is not evidence of anything."""
    lonely = json.loads(json.dumps(next(e for e in BATCH["events"] if e["kind"] == "page")))
    lonely["at"] = "2026-08-31T23:59:00.000Z"  # hours after every gesture
    lonely["url"] = "https://wms.example/reports/daily"
    lonely["page_kind"] = "navigated"

    client.post("/v1/observations", json=_with([lonely], "bat_lonely_page"), headers=_auth())

    rows = store.query(
        "SELECT at, payload FROM orphan_pages WHERE batch_id = ?", ("bat_lonely_page",)
    )

    assert len(rows) == 1
    assert rows[0]["at"] == "2026-08-31T23:59:00.000Z"
    stored = json.loads(rows[0]["payload"])
    assert stored["url"] == "https://wms.example/reports/daily"
    assert stored["page_kind"] == "navigated"


# --- What a pass proposed, once anything has proposed it ----------------------


def test_the_workflows_route_is_empty_before_anything_is_mined(client: TestClient) -> None:
    assert client.get("/v1/workflows", headers=_auth()).json()["workflows"] == []


def test_mining_needs_the_token(client: TestClient) -> None:
    assert client.post("/v1/mine").status_code == 401


def test_the_workflows_route_carries_the_steps_and_the_pass_that_found_them(
    client: TestClient, store: Store
) -> None:
    """The page draws a step's words, its system and how many gestures prove
    it. A route that returned the workflow row alone would render every job as
    a title with nothing under it."""
    from rig.workflows import Step, Workflow, save_workflow

    save_workflow(
        store,
        Workflow(
            id="wfl_1",
            tenant="new",
            title="create a supplier",
            narrative="in two systems",
            systems=["https://wms.example", "https://sap.example"],
            steps=[Step(order=0, says="type the code", system="https://wms.example", cites=["a"])],
            parameters=[{"name": "supplier"}],
            unproven=["a click nobody could place"],
            pass_id="pas_1",
        ),
    )

    body = client.get("/v1/workflows", headers=_auth()).json()["workflows"][0]

    assert body["title"] == "create a supplier"
    assert body["systems"] == ["https://wms.example", "https://sap.example"]
    assert body["steps"] == [
        {
            "order": 0,
            "says": "type the code",
            "system": "https://wms.example",
            "cites": ["a"],
            "parameters": [],
        }
    ]
    # The pass that found it, not a price of its own: the whole pass's bill
    # drawn once per workflow was the same number three times over.
    assert body["pass_id"] == "pas_1"
    # The step's siblings are emitted; the workflow's own were not.
    assert body["unproven"] == ["a click nobody could place"]
    assert body["parameters"] == [{"name": "supplier"}]


def test_the_page_escapes_a_workflow_the_model_wrote_out_of_a_hostile_page() -> None:
    """A workflow's title, narrative and step words are model output over
    captured page content -- the same chain as an intent's `why`, one view
    over. A WMS field named `<img src=x onerror=...>` reaches this page
    through it."""
    attack = "<img src=x onerror=alert(1)>"
    rendered = _run_page(
        f"""
        console.log(job({{
          title: {json.dumps(attack)},
          narrative: {json.dumps(attack)},
          systems: [{json.dumps(attack)}],
          pass_id: "pas_1",
          steps: [{{ order: {json.dumps(attack)}, says: {json.dumps(attack)},
                    system: {json.dumps(attack)}, cites: ["a"] }}],
        }}));
        """
    )

    assert "<img" not in rendered
    assert rendered.count("&lt;img src=x onerror=alert(1)&gt;") == 6
    assert "1 cited" in rendered


def test_a_pass_over_the_route_accounts_for_every_workflow_it_proposed(
    client: TestClient,
) -> None:
    """proposed, kept, refused, already known -- and what it did not read. A
    body that reported only `kept` would turn every other outcome into a
    number that came out lower than expected."""
    body = client.post("/v1/mine", headers=_auth()).json()

    assert body["proposed"] == 0
    assert body["kept"] == 0
    assert body["rejections"] == []
    assert body["resolutions"] == []
    assert body["window"] == 0
    assert body["left_out"] == 0
    assert body["lost_pool"] == []
    # The fake had no answer queued, so this pass was refused. `lopsided` is a
    # verdict on where a model's citations fell and there was no model answer
    # to judge -- the reason it is False here rather than True on coverage 0.0.
    assert body["error"] == "the fake ran out of answers"
    assert body["coverage"]["lopsided"] is False


# --- Open item 2: the rig's own token out of the browser's address bar --------


def test_the_token_arrives_in_the_url_and_does_not_stay_there() -> None:
    """`?token=...` is the rig's credential in browser history, in every
    screenshot of this window, and in the referrer of anything the page loads.
    Arriving that way is how the operator gets here; still being there
    afterwards is the defect. The page's own `readToken()` runs at module load,
    so this reads back what it did to the address bar."""
    out = _run_page(
        """
        console.log(JSON.stringify({
          sent: head.headers.Authorization,
          bar: history.replaced,
          kept: sessionStorage.getItem(TOKEN_KEY),
        }));
        """,
        browser=_browser("http://rig.test/console?stream=str_1&token=sup3r-secret#top"),
    )
    seen = json.loads(out)

    assert seen["sent"] == "Bearer sup3r-secret", "the token from the URL was not used"
    assert seen["kept"] == "sup3r-secret", "nothing would survive the address-bar wipe"
    assert seen["bar"] == ["/console?stream=str_1#top"], (
        "the token is still in the address bar, or the rest of the URL was lost with it"
    )
    assert "sup3r-secret" not in seen["bar"][0]


def test_a_reload_with_no_token_in_the_url_still_has_one() -> None:
    """The wipe is only safe if the second load still authenticates. Calling
    `readToken()` again with a bare URL is that second load: sessionStorage is
    the same tab's, and the token has to come back out of it."""
    out = _run_page(
        """
        const first = readToken();
        globalThis.location = { href: "http://rig.test/console" };
        console.log(JSON.stringify([first, readToken()]));
        """,
        browser=_browser("http://rig.test/console?token=sup3r-secret"),
    )

    assert json.loads(out) == ["sup3r-secret", "sup3r-secret"]


def test_no_token_anywhere_falls_back_to_the_rig_s_own_default() -> None:
    """Absent means "assume a rig left at its defaults", not "send nothing and
    draw a blank page". `config.py`'s `ingest_token` default is this string, so
    a scratch rig is reachable with no token in the URL at all -- and a rig
    with a real token answers 401, which the console reports."""
    out = _run_page("console.log(head.headers.Authorization);")

    assert out.strip() == "Bearer dev-only-not-a-secret"


def test_a_pass_the_model_refused_is_not_a_pass_that_found_nothing(store: Store) -> None:
    """`proposed: 0, kept: 0` is also what an honest empty day looks like. A
    refused or failed call reaches the loop as an Answer carrying a reason and
    no data; the route dropped it, so the two rendered identically."""

    def passing(answer: Answer) -> dict[str, Any]:
        app = build_app(
            store=Store(store.path),
            asker=FakeAsker(answer),
            token=TOKEN,
            tenant="new",
            read_on_ingest=False,
        )
        return dict(TestClient(app).post("/v1/mine", headers=_auth()).json())

    refused = passing(Answer(error="503 UNAVAILABLE", unpriced=True))
    empty = passing(Answer(data={"workflows": []}, cost_usd=0.01))

    assert refused["error"] == "503 UNAVAILABLE"
    assert empty["error"] is None
    assert refused["proposed"] == empty["proposed"] == 0
    # And on record afterwards, not only in the response that reported it.
    errors = [row["error"] for row in store.query("SELECT error FROM passes ORDER BY started_at")]
    assert errors == ["503 UNAVAILABLE", None]


async def test_the_mining_bill_is_the_sum_of_the_passes_not_of_the_workflows(
    store: Store,
) -> None:
    """Two $0.04 passes that found five workflows between them cost $0.08. The
    same figure copied onto each workflow summed to $0.20, and grew with how
    well the passes did."""
    from rig.mine import mine
    from rig.workflows import known_workflows

    save_batch(store, Batch.model_validate(BATCH), "new")
    ids = [row["id"] for row in store.query("SELECT id FROM gestures ORDER BY at")]

    def found(*pairs: tuple[int, int]) -> Answer:
        return Answer(
            data={
                "workflows": [
                    {
                        "title": f"job {a}",
                        "narrative": "n",
                        "systems": ["http://127.0.0.1:63319"],
                        "steps": [
                            {
                                "order": 0,
                                "cites": ids[a:b],
                                "says": "do it",
                                "system": "http://127.0.0.1:63319",
                            }
                        ],
                    }
                    for a, b in pairs
                ]
            },
            cost_usd=0.04,
        )

    asker = FakeAsker(found((0, 1), (1, 2), (2, 3)), found((3, 4), (4, 5)))
    await mine(store, tenant="new", asker=asker, model="m")
    await mine(store, tenant="new", asker=asker, model="m")

    client = TestClient(
        build_app(store=store, asker=asker, token=TOKEN, tenant="new", read_on_ingest=False)
    )
    body = client.get("/v1/spend", headers=_auth()).json()

    assert len(known_workflows(store, "new")) == 5
    assert body["passes"] == 2
    assert body["mining_usd"] == 0.08
    assert body["mining_unpriced"] == 0


def test_the_stored_redaction_marker_is_the_one_people_grep_for(store: Store) -> None:
    """json.dumps' default ensure_ascii wrote «redacted» into the store as
    \\u00abredacted\\u00bb -- a form nothing else in this system uses. Measured on
    the real acme store before the fix: 272 markers on disk, every one escaped
    and none of them literal, so a reviewer grepping the evidence for the
    marker the browser writes came back empty. gesture_json never had this
    problem, because pydantic's model_dump_json does not escape -- so one row
    held the marker in two different spellings, in two adjacent columns."""
    batch = json.loads(json.dumps(BATCH))
    request = next(e for e in batch["events"] if e["kind"] == "request")["request"]
    request["request_headers"]["Authorization"] = "Bearer sk-live-abcdef"

    save_batch(store, Batch.model_validate(batch), "acme")
    stored = "".join(row["requests"] for row in store.query("SELECT requests FROM gestures"))

    assert "«redacted»" in stored
    assert "\\u00ab" not in stored


def test_the_four_fields_the_protocol_carries_are_kept(store: Store) -> None:
    """`page_url`, `started_at`, `ended_at` and `recording_id` were parsed,
    validated, redacted -- and then dropped on the floor, which is how a field
    someone eventually assumes is available turns out never to have been. Same
    reason `shot_ref` and `ax_ref` were deleted in Task 8; these four earn their
    place instead, so they are stored."""
    batch = json.loads(json.dumps(BATCH))
    batch["mode"] = "teaching"
    batch["recording_id"] = "rec_42"

    save_batch(store, Batch.model_validate(batch), "acme")

    row = store.query("SELECT * FROM batches")[0]
    assert row["started_at"] == batch["started_at"]
    assert row["ended_at"] == batch["ended_at"]
    assert row["recording_id"] == "rec_42"

    # The tab's url, which is not the frame's: `url` is what the gesture
    # happened in, `page_url` is the address an operator would type.
    gesture = next(e for e in batch["events"] if e["kind"] == "gesture")
    stored = store.query("SELECT page_url FROM gestures")
    assert stored, "no gesture reached the store"
    assert {r["page_url"] for r in stored} == {gesture["page_url"]}
    rebuilt = _row_to_gesture(store.query("SELECT * FROM gestures")[0])
    assert rebuilt.page_url == gesture["page_url"]


def test_a_credential_in_the_tab_url_never_reaches_the_store(store: Store) -> None:
    """page_url goes through the same parse-boundary redaction every other url
    does. Storing it is only safe because that rule already ran."""
    batch = json.loads(json.dumps(BATCH))
    for event in batch["events"]:
        if event["kind"] == "gesture":
            event["page_url"] = "https://wms.example/back?access_token=sk-live-abcdef"

    save_batch(store, Batch.model_validate(batch), "acme")
    stored = store.query("SELECT page_url FROM gestures")[0]["page_url"]

    assert "sk-live-abcdef" not in stored
    assert stored == "https://wms.example/back?access_token=«redacted»"


def test_the_pool_route_reports_what_stopped_being_offered_and_why(
    client: TestClient, store: Store
) -> None:
    """pool.py says retirement must leave a record. `retired_entries` had no
    reader over the wire, so a window that quietly stopped carrying yesterday's
    tail looked exactly like one with nothing left to carry."""
    from rig.pool import K_POOL_AGE, add_unclaimed, age_pool

    add_unclaimed(store, "new", ["ges_old"], set())
    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "new")
    add_unclaimed(store, "new", ["ges_fresh"], set())

    body = client.get("/v1/pool", headers=_auth()).json()

    assert body["pooled"] == ["ges_fresh"]
    assert [entry["gesture_id"] for entry in body["retired"]] == ["ges_old"]
    assert body["retired"][0]["reason"] == "passes"
    assert body["retired"][0]["age"] == K_POOL_AGE + 1


def test_the_pool_route_answers_for_this_tenant_only(client: TestClient, store: Store) -> None:
    from rig.pool import add_unclaimed

    add_unclaimed(store, "new", ["ges_ours"], set())
    add_unclaimed(store, "other", ["ges_theirs"], set())

    body = client.get("/v1/pool", headers=_auth()).json()

    assert body["pooled"] == ["ges_ours"]


def _other_tenants_gesture(store: Store, gesture_id: str = "ges_theirs") -> None:
    """One gesture belonging to a tenant this app was not built for."""
    store.execute(
        "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, gesture_json)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            gesture_id,
            "other",
            "dev_theirs",
            "bat_theirs",
            9999.0,
            json.dumps({"kind": "click", "at": 9999.0, "url": "https://theirs.example/"}),
        ),
    )


def test_the_routes_answer_for_this_tenant_and_no_other(client: TestClient, store: Store) -> None:
    """mine, pool and workflows all filter on tenant; these three did not. A
    second tenant in one store made /v1/spend report someone else's bill."""
    client.post("/v1/observations", json=BATCH, headers=_auth())
    _other_tenants_gesture(store)
    from rig.api import save_intent
    from rig.records import Intent

    save_intent(store, Intent(gesture_id="ges_theirs", tenant="other", act="x", cost_usd=9.99))
    store.execute(
        "INSERT INTO passes (id, tenant, started_at, cost_usd) VALUES (?, ?, ?, ?)",
        ("pas_theirs", "other", "2026-01-01T00:00:00+00:00", 4.5),
    )

    streams = client.get("/v1/streams", headers=_auth()).json()
    gestures = client.get("/v1/gestures", headers=_auth()).json()
    spend = client.get("/v1/spend", headers=_auth()).json()

    assert [row["stream_id"] for row in streams["streams"]] == ["dev_browsertest"]
    assert "ges_theirs" not in [row["id"] for row in gestures["gestures"]]
    assert spend["gestures"] == 7, "another tenant's gestures are not our backlog"
    assert spend["gestures_read"] == 0
    assert spend["cost_usd"] == 0.0, "another tenant's readings are not our bill"
    assert spend["passes"] == 0 and spend["mining_usd"] == 0.0


async def test_the_reading_loop_pays_for_this_tenant_only(store: Store) -> None:
    """The reading is what costs money. Unscoped, this loop read -- and billed
    us for -- gestures no pass of ours will ever mine."""
    save_batch(store, Batch.model_validate(BATCH), "new")
    _other_tenants_gesture(store)
    asker = FakeAsker(*[Answer(data={"act": "x"}, cost_usd=0.001) for _ in range(9)])

    read = await read_new_gestures(store, asker, "m", "new")

    assert read == 7
    assert store.query("SELECT count(*) AS n FROM intents WHERE tenant = 'other'")[0]["n"] == 0


async def test_the_spend_route_says_how_much_of_the_bill_was_thinking(store: Store) -> None:
    """Thinking is billed at the output rate and is ~84% of billed output on
    Flash. `Answer.thought_tokens` was carried out of the SDK, priced, and then
    reached no reader at all -- so the bill said the readings were expensive and
    nothing said what had been paid for."""
    from rig.api import save_intent
    from rig.mine import mine
    from rig.records import Intent

    save_batch(store, Batch.model_validate(BATCH), "new")
    reading = FakeAsker(
        *[Answer(data={"act": "x"}, out_tokens=100, thought_tokens=84) for _ in range(7)]
    )
    await read_new_gestures(store, reading, "m", "new")
    save_intent(store, Intent(gesture_id="ges_hand", tenant="new", out_tokens=10, thought_tokens=6))
    await mine(
        store,
        tenant="new",
        asker=FakeAsker(Answer(data={"workflows": []}, out_tokens=900, thought_tokens=800)),
        model="m",
    )

    client = TestClient(
        build_app(store=store, asker=reading, token=TOKEN, tenant="new", read_on_ingest=False)
    )
    body = client.get("/v1/spend", headers=_auth()).json()

    assert body["out_tokens"] == 7 * 100 + 10
    assert body["thought_tokens"] == 7 * 84 + 6 + 800


def test_an_integrity_failure_that_is_not_a_duplicate_batch_is_not_called_one(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`already_had_it` is what the extension reads to drop a batch it has
    already sent. Returned for ANY integrity failure, it told the extension
    that a batch nothing stored was handled -- and those events are gone."""
    from rig import correlate as correlate_module

    monkeypatch.setattr(correlate_module, "new_gesture_id", lambda: "ges_the_same_twice")

    with pytest.raises(sqlite3.IntegrityError, match="gestures.id"):
        save_batch(store, Batch.model_validate(BATCH), "new")

    assert store.query("SELECT count(*) AS n FROM batches")[0]["n"] == 0, "the claim rolled back"


def test_a_batch_that_really_was_sent_twice_is_still_a_no_op(store: Store) -> None:
    """The case the narrowed except keeps."""
    save_batch(store, Batch.model_validate(BATCH), "new")

    accepted, already, _ = save_batch(store, Batch.model_validate(BATCH), "new")

    assert (accepted, already) == (0, True)


def test_the_header_shows_how_much_of_the_bill_was_thinking() -> None:
    """The bill's biggest component on Flash, and the line where a person
    reads the bill. /v1/spend carries it; the header dropped it."""
    rendered = _run_page(
        """
        const base = { gestures: 9, gestures_read: 7, cost_usd: 0.0259,
                       per_gesture_usd: 0.0037, unpriced: 0, unusable: 0,
                       thought_tokens: 0 };
        console.log(JSON.stringify([
          spendLine(base),
          spendLine({ ...base, thought_tokens: 5000 }),
        ]));
        """
    )
    silent, thinking = json.loads(rendered)

    assert "thought" not in silent, "a model that thought nothing says nothing"
    assert "5000" in thinking and "thought" in thinking


def test_reading_stops_at_the_daily_cap_and_capture_does_not(
    store: Store, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """read_on_ingest bills per gesture as capture arrives, so an unattended
    week spends whatever the operator's day produces. The cap stops the asking,
    never the mirroring: the evidence is still stored, so raising it tomorrow
    reads what today declined."""
    from rig.config import Settings, settings

    monkeypatch.setattr(
        "rig.api.settings",
        lambda: Settings(gemini_api_key="x", tenant="new", daily_usd_cap=0.001),
    )
    settings.cache_clear()
    save_batch(store, Batch.model_validate(BATCH), "new")
    store.execute(
        "INSERT INTO intents (gesture_id, tenant, cost_usd, created_at)"
        " VALUES ('ges_spent', 'new', 9.99, ?)",
        (datetime.now(tz=UTC).isoformat(),),
    )

    with caplog.at_level(logging.WARNING):
        written = asyncio.run(
            _read_unread(store, FakeAsker(Answer(data={"act": "x"})), "gemini-3.8-flash", "new")
        )

    assert written == 0, "over the cap, nothing is read"
    assert "daily cap reached" in caplog.text, "and it says so rather than going quiet"
    assert store.query("SELECT count(*) AS n FROM gestures WHERE tenant = 'new'")[0]["n"] > 0, (
        "the evidence is still there to read tomorrow"
    )


def test_a_day_of_unpriced_readings_stops_the_asking_too(
    store: Store, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The one failure PRICES cannot fix, and the cap was blind to it.

    A model name the table never knew about records `cost_usd = 0.0` with
    `unpriced = 1` -- honest, and useless to a guard that sums the column. This
    deployment already lived it: the run that proved the architecture billed
    $1.12 and every row said free. An unattended week on a new preview name
    would spend without limit while `SUM(cost_usd)` read zero, which is the
    exact shape of the accident the cap exists to prevent.
    """
    from rig.config import Settings, settings

    monkeypatch.setattr(
        "rig.api.settings",
        lambda: Settings(gemini_api_key="x", tenant="new", daily_usd_cap=5.0),
    )
    settings.cache_clear()
    save_batch(store, Batch.model_validate(BATCH), "new")
    store.execute(
        "INSERT INTO intents (gesture_id, tenant, cost_usd, unpriced, created_at)"
        " VALUES ('ges_blind', 'new', 0.0, 1, ?)",
        (datetime.now(tz=UTC).isoformat(),),
    )

    with caplog.at_level(logging.WARNING):
        written = asyncio.run(
            _read_unread(store, FakeAsker(Answer(data={"act": "x"})), "gemini-3.8-flash", "new")
        )

    assert written == 0, "a reading nobody could price is not a reading known to be free"
    assert "unpriced" in caplog.text, "and the log says which of the two caps fired"


def test_a_workflows_evidence_is_served_in_the_shape_a_runner_takes(
    client: TestClient, store: Store
) -> None:
    """`/v1/workflows` serves the citations and `/v1/gestures` reduces a target
    to its NAME, for a person reading a listing. Between them nothing served
    the target itself, so the backend's bridge -- whose whole purpose is turning
    a mined step into something replayable -- had no route to read and had to
    be pointed at a SQLite column. A bridge only usable by something holding
    the rig's database file is not a bridge."""
    save_batch(store, Batch.model_validate(BATCH), "new")
    ids = [row["id"] for row in store.query("SELECT id FROM gestures ORDER BY at")]
    store.execute(
        "INSERT INTO workflows (id, tenant, title, narrative, systems, shape_key, pass_id,"
        " parameters, unproven, created_at)"
        """ VALUES ('wfl_1', 'new', 't', 'n', '[]', '["k"]', 'pas_1', '[]', '[]', ?)""",
        (datetime.now(tz=UTC).isoformat(),),
    )
    store.execute(
        "INSERT INTO workflow_steps (workflow_id, ord, says, system, cites, parameters)"
        " VALUES ('wfl_1', 0, 'do it', NULL, ?, '[]')",
        (json.dumps([*ids, "ges_that_is_gone"]),),
    )

    found = client.get("/v1/workflows/wfl_1/evidence", headers=_auth())
    assert found.status_code == 200, found.text[:300]
    body = found.json()

    assert set(body["gestures"]) == set(ids)
    assert set(body["requests"]) == set(ids)
    assert body["missing"] == ["ges_that_is_gone"], "a citation with no evidence is reported"
    assert body["recordings"], "the capture streams, which Provenance needs"
    first = body["gestures"][ids[0]]
    assert isinstance(first.get("target"), dict) or first.get("kind") == "scroll", (
        "the target itself, not the name /v1/gestures reduces it to"
    )


def test_evidence_for_a_workflow_nobody_has_is_a_404(client: TestClient) -> None:
    assert client.get("/v1/workflows/nope/evidence", headers=_auth()).status_code == 404


def test_evidence_is_not_served_without_the_token(client: TestClient) -> None:
    """Every gesture a workflow cites, which is the operator's own screen."""
    assert client.get("/v1/workflows/wfl_1/evidence").status_code == 401


def test_a_run_is_started_from_the_form_door_and_can_be_read_back(
    client: TestClient, store: Store
) -> None:
    from rig.channel import Answer as Reply
    from rig.channel import FakeChannel
    from rig.workflows import Step, Workflow, save_workflow

    save_batch(store, Batch.model_validate(BATCH), "new")
    ids = [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]
    save_workflow(
        store,
        Workflow(
            id="wfl_1",
            tenant="new",
            title="t",
            narrative="n",
            steps=[Step(order=0, says="type", system=None, cites=[ids[0]])],
        ),
    )
    fake = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "u"})] * 4,
            "screenshot": [
                Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "Save"})
            ]
            * 4,
            "ui.perform": [
                Reply(
                    ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}
                )
            ],
        }
    )
    client.app.state.channel = fake
    client.app.state.asker = FakeAsker(
        Answer(data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""}),
        Answer(data={"held": True, "why": ""}),
    )

    started = client.post(
        "/v1/runs",
        json={
            "workflow_id": "wfl_1",
            "values": {},
            "live": False,
            "device_id": "dev_test",
            "allow_focus": True,
            "started_by": "form",
        },
        headers=_auth(),
    )
    assert started.status_code == 202
    run_id = started.json()["run_id"]

    for _ in range(50):
        body = client.get(f"/v1/runs/{run_id}", headers=_auth()).json()
        if body["outcome"] != "running":
            break
        time.sleep(0.05)
    assert body["outcome"] == "held"
    assert body["steps"][0]["verdict"] == "held" and body["steps"][0]["verdict_by"] == "screen"


def test_a_run_against_a_device_that_is_not_connected_is_refused_at_the_door(
    client: TestClient,
) -> None:
    refused = client.post(
        "/v1/runs",
        json={
            "workflow_id": "wfl_1",
            "values": {},
            "live": False,
            "device_id": "dev_nobody",
            "allow_focus": True,
            "started_by": "form",
        },
        headers=_auth(),
    )
    assert refused.status_code == 409


def test_a_device_already_running_a_job_will_not_take_a_second(
    client: TestClient, store: Store
) -> None:
    """One browser, one hand. Two runs driving the same window interleave
    clicks into a form neither of them can then read back."""
    from rig.channel import FakeChannel
    from rig.runs import Run, save_run
    from rig.workflows import Step, Workflow, save_workflow

    save_workflow(
        store,
        Workflow(
            id="wfl_1",
            tenant="new",
            title="t",
            narrative="n",
            steps=[Step(order=0, says="s", system=None, cites=[])],
        ),
    )
    client.app.state.channel = FakeChannel({})
    save_run(
        store,
        Run(
            id="run_busy",
            tenant="new",
            workflow_id="wfl_1",
            device_id="dev_test",
            values={},
            started_by="form",
            live=False,
            allow_focus=True,
            started_at="2026-01-01T00:00:00+00:00",
        ),
    )

    refused = client.post(
        "/v1/runs",
        json={
            "workflow_id": "wfl_1",
            "values": {},
            "live": False,
            "device_id": "dev_test",
            "allow_focus": True,
            "started_by": "form",
        },
        headers=_auth(),
    )

    assert refused.status_code == 409
    assert "run_busy" in refused.json()["detail"]
    assert store.query("SELECT count(*) AS n FROM runs")[0]["n"] == 1


def test_chat_offers_and_never_starts(client: TestClient, store: Store) -> None:
    from rig.workflows import Step, Workflow, save_workflow

    save_workflow(
        store,
        Workflow(
            id="wfl_1",
            tenant="new",
            title="create a client",
            narrative="n",
            steps=[Step(order=0, says="s", system=None, cites=["g"])],
            parameters=[{"name": "clientCode", "seen_values": ["A"]}],
        ),
    )
    client.app.state.asker = FakeAsker(
        Answer(data={"workflow_id": "wfl_1", "values": {"clientCode": "NEW9"}, "missing": []})
    )

    offered = client.post(
        "/v1/chat", json={"utterance": "create client NEW9"}, headers=_auth()
    ).json()

    assert offered == {"workflow_id": "wfl_1", "values": {"clientCode": "NEW9"}, "missing": []}
    assert store.query("SELECT count(*) AS n FROM runs")[0]["n"] == 0, (
        "saying it offers the work; pressing start authorises it"
    )


def test_the_stop_button_flips_the_flag_and_tells_the_browser(client: TestClient) -> None:
    from rig.channel import Answer as Reply
    from rig.channel import FakeChannel
    from rig.runner import Aborts

    fake = FakeChannel({"abort": [Reply(ok=True, result={"aborted": True})]})
    client.app.state.channel = fake
    assert client.post(
        "/v1/runs/run_x/abort", json={"device_id": "dev_test"}, headers=_auth()
    ).json() == {"aborted": True}
    assert Aborts.is_aborted("run_x")
    assert [s for s in fake.sent if s["kind"] == "abort"] == [
        {
            "device_id": "dev_test",
            "kind": "abort",
            "payload": {"run_id": "run_x"},
            "run_id": "run_x",
        }
    ], "the browser is told which run to drop, once"
    Aborts.forget("run_x")


def test_devices_lists_what_is_connected(client: TestClient) -> None:
    assert client.get("/v1/devices", headers=_auth()).json() == {"devices": []}


def _idle_workflow(store: Store, parameters: list[dict[str, Any]] | None = None) -> None:
    """A workflow whose one step cites nothing, so a run of it plans nothing,
    sends nothing, and stops -- the door is what these tests are about."""
    from rig.workflows import Step, Workflow, save_workflow

    save_workflow(
        store,
        Workflow(
            id="wfl_1",
            tenant="new",
            title="t",
            narrative="n",
            steps=[Step(order=0, says="s", system=None, cites=[])],
            parameters=parameters or [],
        ),
    )


def _start(client: TestClient, **body: Any) -> Any:
    return client.post(
        "/v1/runs",
        json={"workflow_id": "wfl_1", "device_id": "dev_test", "started_by": "form", **body},
        headers=_auth(),
    )


def test_a_declared_parameter_left_blank_is_refused_before_anything_is_started(
    client: TestClient, store: Store
) -> None:
    """The planner falls back to the value the recording happened to contain
    when a parameter has none. That fallback exists for a step nobody
    parameterised; for a declared parameter left blank it would quietly perform
    the job with somebody else's client code."""
    from rig.channel import FakeChannel

    _idle_workflow(store, [{"name": "clientCode", "seen_values": ["A"]}])
    client.app.state.channel = FakeChannel({})

    refused = _start(client, values={})

    assert refused.status_code == 400
    assert "clientCode" in refused.json()["detail"]
    assert store.query("SELECT count(*) AS n FROM runs")[0]["n"] == 0


def test_a_value_that_is_not_a_string_is_refused_and_never_echoed(
    client: TestClient, store: Store
) -> None:
    from rig.channel import FakeChannel

    _idle_workflow(store, [{"name": "clientCode", "seen_values": ["A"]}])
    client.app.state.channel = FakeChannel({})

    refused = _start(client, values={"clientCode": {"nested": "hunter2"}})

    assert refused.status_code == 400
    assert "hunter2" not in refused.text, "a refusal names the parameter, never the value"
    assert _start(client, values=["clientCode"]).status_code == 400
    assert store.query("SELECT count(*) AS n FROM runs")[0]["n"] == 0


def test_the_device_is_claimed_before_the_press_answers(
    client: TestClient, store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `running` row is written by the handler, not by the task it spawns.

    Written by the task, the second press lands in the window between
    `create_task` and that task's first slice, reads no busy run, and puts a
    second hand on the same browser. The spawn is stubbed out entirely so the
    window is the whole test: nothing but the handler can have written the row
    the second press must see.
    """
    from rig import api
    from rig.channel import FakeChannel

    _idle_workflow(store)
    client.app.state.channel = FakeChannel({})
    monkeypatch.setattr(api, "_spawn_run", lambda work: work.close())

    first, second = _start(client, values={}), _start(client, values={})

    assert (first.status_code, second.status_code) == (202, 409)
    assert first.json()["run_id"] in second.json()["detail"]
    assert store.query("SELECT count(*) AS n FROM runs")[0]["n"] == 1


def test_a_first_execution_is_dry_unless_the_caller_says_otherwise(
    client: TestClient, store: Store
) -> None:
    from rig.channel import FakeChannel
    from rig.runs import load_run

    _idle_workflow(store)
    client.app.state.channel = FakeChannel({})

    started = _start(client, values={})

    run = load_run(store, "new", started.json()["run_id"])
    assert run is not None and run.live is False, "live is a thing a person asks for"


def test_the_stop_button_works_on_a_browser_that_has_already_gone(client: TestClient) -> None:
    """The flag is the authority; telling the browser is best effort. A run
    whose browser died is exactly the run somebody presses stop on."""
    from collections.abc import Mapping

    from rig.channel import Answer as Reply
    from rig.channel import DeviceUnreachable, FakeChannel
    from rig.runner import Aborts

    class _Gone(FakeChannel):
        async def send(
            self,
            device_id: str,
            *,
            kind: str,
            payload: Mapping[str, object],
            run_id: str | None = None,
            deadline_s: float | None = None,
        ) -> Reply:
            raise DeviceUnreachable("dev_test is not connected")

    client.app.state.channel = _Gone({})
    stopped = client.post("/v1/runs/run_y/abort", json={"device_id": "dev_test"}, headers=_auth())

    assert stopped.status_code == 200 and stopped.json() == {"aborted": True}
    assert Aborts.is_aborted("run_y")
    Aborts.forget("run_y")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/v1/devices"),
        ("post", "/v1/runs"),
        ("get", "/v1/runs/run_x"),
        ("post", "/v1/runs/run_x/abort"),
        ("post", "/v1/chat"),
    ],
)
def test_no_door_of_the_runner_opens_without_the_token(
    client: TestClient, method: str, path: str
) -> None:
    """Every one of these either drives the operator's own browser or reads
    what it did."""
    assert client.request(method, path, json={}).status_code == 401


# --- Task 9: the page starts a run, watches it, and stops it ------------------


def test_the_page_can_start_watch_and_stop_a_run() -> None:
    page = (Path(__file__).resolve().parents[1] / "src/rig/web/index.html").read_text()
    for needed in (
        "/v1/devices",
        "/v1/runs",
        "/abort",
        "what a live run would have sent",
        'type="checkbox"',
        "stop",
    ):
        assert needed in page, needed


def test_the_page_escapes_a_run_and_says_when_a_step_could_not_be_priced() -> None:
    """A run's text is a model's plan over a page the extension read back --
    the same chain as an intent's `why`, and the same reason to escape it. The
    substring test above passes with esc() dropped from every one of them, so
    render a run whose every field is a script tag and count.

    The unpriced step is `line()`'s three states again, one table over: a step
    billed on a model missing from PRICES drawn as "$0.0000" is a price the
    page made up.
    """
    hostile = "<img src=x onerror=\"go('x')\">"
    rendered = _run_page(
        """
        // Both quote characters: esc() escaping them is what keeps a value
        // out of the attribute it is written into, and nothing else on the
        // page would notice if it stopped.
        const hostile = `<img src=x onerror="go('x')">`;
        // Not `step`: the page already has a function by that name.
        const one = { order: 1, says: hostile, verdict: "held", verdict_by: "model",
                      reason: hostile, matched_by: hostile, stale: false,
                      cost_usd: 0.0031, unpriced: false };
        const run = {
          outcome: "held", cost_usd: 0.0062, unpriced: false,
          steps: [one, { ...one, order: 2 }],
          // No method/url/body: a withheld write whose step has no recorded
          // call carries only the planned command, and that is the whole of
          // what a live run would have sent.
          withheld: [{ step: 2, planned: { kind: "click", payload: { text: hostile } } }],
        };
        console.log(JSON.stringify([
          runView(run),
          runView({ ...run, outcome: "running" }),
          ranStep({ ...one, cost_usd: 0, unpriced: true }),
          ranStep({ ...one, cost_usd: 0, unpriced: false }),
          // A prefill read off a warehouse page, landing inside value="...".
          paramField({ name: "clientCode", seen_values: [`" onmouseover=alert(1) x="`] }),
        ]));
        """
    )
    held, running, unpriced, free, field = json.loads(rendered)

    assert hostile not in held, "a run's text reaches the DOM unescaped"
    # says, reason and matched_by on each of two steps, plus the withheld
    # payload: seven fields, every one of them through esc(). The seventh has
    # been through JSON.stringify first, so it carries backslashes the other
    # six do not -- match the opening of the tag rather than the whole of it.
    assert held.count("&lt;img src=x onerror=") == 7, held
    assert held.count("&quot;go(&#39;x&#39;)&quot;&gt;") == 6, held
    assert "what a live run would have sent" in held
    assert "click" in held, "a withheld write with no recorded call draws an empty box"
    assert 'class="stop"' in running, "a running run cannot be stopped"
    assert 'class="stop"' not in held, "a finished run still offers a stop button"
    assert 'class="close"' in held, "a finished run view cannot be dismissed"
    assert 'class="close"' not in running, "a run still going is offered a close instead of a stop"
    assert "unpriced" in unpriced and "$0.0000" not in unpriced
    assert "$0.0000" in free, "an honestly-free step and an unpriced one read the same"
    # The attribute context. Between tags, a lone `"` is harmless and a page
    # that stopped escaping it looks fine; inside value="..." it closes the
    # attribute and everything after it is markup the browser runs.
    assert '" onmouseover' not in field, f"the value attribute closes early: {field}"
    assert "&quot; onmouseover=alert(1) x=&quot;" in field, field


def test_the_redraw_carries_an_open_runner_into_the_fresh_card() -> None:
    """The job list is redrawn every three seconds. Holding that off while a
    runner was open deadlocked -- the skipped redraw was the one that would
    have removed the form -- so the cards are always rebuilt and the live boxes
    are moved across instead. Moved, not re-rendered: the same node, because
    what has to survive is a half-typed value and the div a poll still holds a
    reference to, neither of which is in the markup.
    """
    rendered = _run_page(
        """
        globalThis.CSS = { escape: (s) => s };
        const box = (id, innerHTML) => ({ id, innerHTML });
        const root = (boxes) => ({
          boxes,
          querySelectorAll: () => boxes,
          querySelector(selector) {
            const seat = boxes.find((b) => b.id === selector.slice(1));
            if (seat) seat.replaceWith = (live) => { boxes[boxes.indexOf(seat)] = live; };
            return seat ?? null;
          },
        });
        const open = box("runner-a", "<form>typed</form>");
        const orphan = box("runner-gone", "<form>its job vanished</form>");
        const into = root([box("runner-a", ""), box("runner-b", "")]);
        carryOver(root([open, orphan, box("runner-b", "")]), into);
        console.log(JSON.stringify({
          boxes: into.boxes.map((b) => [b.id, b.innerHTML]),
          same: into.boxes[0] === open,
        }));
        """
    )
    got = json.loads(rendered)

    assert got["same"], "the box was re-rendered, so the typed values and the poll's div are gone"
    assert got["boxes"] == [["runner-a", "<form>typed</form>"], ["runner-b", ""]], got


def test_the_shapes_route_serves_what_shapes_for_computes(client: TestClient, store: Store) -> None:
    _seed_workflow(store)

    got = client.get("/v1/shapes", headers=_auth())

    assert got.status_code == 200
    [shape] = got.json()["shapes"]
    assert shape["id"] == "wfl_1" and shape["parameters"] == [{"name": "clientCode", "at": 0}]


def test_an_offer_and_its_fate_are_recorded(client: TestClient, store: Store) -> None:
    _seed_workflow(store)
    body = {
        "workflow_id": "wfl_1",
        "k": 2,
        "fate": "diverged",
        "device_id": "dev_1",
        "at": "2026-09-06T10:00:00+00:00",
    }

    got = client.post("/v1/offers", json=body, headers=_auth())

    assert got.status_code == 201 and got.json()["offer_id"].startswith("off_")
    rows = store.query("SELECT workflow_id, k, fate, run_id FROM offers")
    assert [tuple(r) for r in rows] == [("wfl_1", 2, "diverged", None)]


def test_an_offer_with_a_fate_nobody_named_is_refused(client: TestClient, store: Store) -> None:
    _seed_workflow(store)
    body = {"workflow_id": "wfl_1", "k": 2, "fate": "maybe", "device_id": "dev_1", "at": "x"}

    assert client.post("/v1/offers", json=body, headers=_auth()).status_code == 400

    body["fate"], body["workflow_id"] = "accepted", "wfl_nope"
    assert client.post("/v1/offers", json=body, headers=_auth()).status_code == 400


def test_a_run_can_start_where_the_operator_left_off(client: TestClient, store: Store) -> None:
    """The offer's Yes. The operator typed the code themselves; the rig is
    being asked to finish the job, not to do it again."""
    from rig.channel import Answer as Reply
    from rig.channel import FakeChannel
    from rig.runs import load_run

    _seed_workflow(store)
    client.app.state.channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 4,
            "screenshot": [
                Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "Save"})
            ]
            * 4,
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})],
        }
    )
    client.app.state.asker = FakeAsker(
        Answer(
            data={"kind": "ui.perform", "action": "click", "value": None, "url": None, "why": ""}
        ),
        Answer(data={"held": True, "why": ""}),
    )
    body = {
        "workflow_id": "wfl_1",
        "values": {"clientCode": "A"},
        "device_id": "dev_test",
        "live": False,
        "from_step": 1,
    }

    got = client.post("/v1/runs", json=body, headers=_auth())

    assert got.status_code == 202
    run_id = got.json()["run_id"]
    for _ in range(50):
        if client.get(f"/v1/runs/{run_id}", headers=_auth()).json()["outcome"] != "running":
            break
        time.sleep(0.05)
    run = load_run(store, "new", run_id)
    assert run is not None and run.steps[0].verdict == "done_by_operator"
    assert run.steps[0].sent is None, "the operator's own step was never sent to the browser"


def test_a_from_step_past_the_job_is_refused(client: TestClient, store: Store) -> None:
    from rig.channel import FakeChannel

    _seed_workflow(store)
    client.app.state.channel = FakeChannel()
    body: dict[str, Any] = {
        "workflow_id": "wfl_1",
        "values": {"clientCode": "A"},
        "device_id": "dev_test",
        "from_step": 2,
    }
    assert client.post("/v1/runs", json=body, headers=_auth()).status_code == 400
    body["from_step"] = -1
    assert client.post("/v1/runs", json=body, headers=_auth()).status_code == 400
    body["from_step"] = True
    assert client.post("/v1/runs", json=body, headers=_auth()).status_code == 400


def test_approve_with_nothing_waiting_is_refused(client: TestClient) -> None:
    assert client.post("/v1/runs/run_x/approve", json={}, headers=_auth()).status_code == 409


def test_approve_needs_no_body(client: TestClient) -> None:
    # A bare POST is a tap; 422 would be the route arguing about a body it
    # never reads.
    assert client.post("/v1/runs/run_x/approve", headers=_auth()).status_code == 409


def test_approve_releases_a_waiting_write(client: TestClient) -> None:
    from rig.runner import Approvals

    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(Approvals.wait_for("run_w", timeout=2))
        loop.run_until_complete(asyncio.sleep(0))
        got = client.post("/v1/runs/run_w/approve", json={}, headers=_auth())
        assert got.status_code == 200 and got.json() == {"approved": True}
        assert loop.run_until_complete(task) is True
    finally:
        loop.close()
