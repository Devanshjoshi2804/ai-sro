"""The rig's one process: take what the extension saw, read it, show it."""

import asyncio
import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, Header, HTTPException, UploadFile
from pydantic import ValidationError

from rig.config import settings
from rig.correlate import correlate
from rig.intents import read_gesture
from rig.models import Asker, GeminiAsker
from rig.records import Gesture, Intent, ValueSeen
from rig.store import Store
from rig.wire import Batch, parse_batch
from rig.wire import Gesture as WireGesture


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def save_batch(store: Store, batch: Batch, tenant: str, rejected: int = 0) -> tuple[int, bool]:
    """Store one batch and its gestures. Idempotent on batch_id."""
    try:
        store.execute(
            "INSERT INTO batches (batch_id, device_id, tenant, mode, received_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (batch.batch_id, batch.device_id, tenant, batch.mode, _now()),
        )
    except sqlite3.IntegrityError:
        return 0, True

    gestures, orphan_requests, orphan_pages = correlate(batch, tenant)

    with store.connect() as connection:
        for gesture in gestures:
            connection.execute(
                "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, url, system,"
                " tab_id, frame_url, gesture_json, requests, page_events)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    gesture.id,
                    gesture.tenant,
                    gesture.stream_id,
                    gesture.batch_id,
                    gesture.at,
                    gesture.url,
                    gesture.system,
                    gesture.tab_id,
                    gesture.frame_url,
                    gesture.gesture.model_dump_json(),
                    json.dumps([r.model_dump(mode="json") for r in gesture.requests]),
                    json.dumps([p.model_dump(mode="json") for p in gesture.page_events]),
                ),
            )
        for orphan in orphan_requests:
            connection.execute(
                "INSERT OR IGNORE INTO orphan_requests (request_id, batch_id, tenant, payload)"
                " VALUES (?, ?, ?, ?)",
                (
                    orphan.request.request_id,
                    batch.batch_id,
                    tenant,
                    orphan.model_dump_json(),
                ),
            )
        for page in orphan_pages:
            connection.execute(
                "INSERT OR IGNORE INTO orphan_pages (batch_id, tenant, at, payload)"
                " VALUES (?, ?, ?, ?)",
                (batch.batch_id, tenant, page.at, page.model_dump_json()),
            )
        connection.execute(
            "UPDATE batches SET accepted = ?, rejected = ? WHERE batch_id = ?",
            (len(gestures), rejected, batch.batch_id),
        )

    return len(gestures), False


def _row_to_gesture(row: sqlite3.Row) -> Gesture:
    return Gesture(
        id=row["id"],
        tenant=row["tenant"],
        stream_id=row["stream_id"],
        batch_id=row["batch_id"],
        at=row["at"],
        url=row["url"],
        system=row["system"],
        tab_id=row["tab_id"],
        frame_url=row["frame_url"],
        gesture=WireGesture.model_validate_json(row["gesture_json"]),
        requests=[],
        page_events=[],
        shot_ref=row["shot_ref"],
    )


def _row_to_intent(row: sqlite3.Row) -> Intent:
    return Intent(
        gesture_id=row["gesture_id"],
        tenant=row["tenant"],
        act=row["act"],
        object=row["object"],
        system=row["system"],
        page=row["page"],
        values_seen=[ValueSeen(**seen) for seen in json.loads(row["values_seen"])],
        continues=row["continues"],
        confidence=row["confidence"],
        why=row["why"],
        model=row["model"],
        in_tokens=row["in_tokens"],
        out_tokens=row["out_tokens"],
        cost_usd=row["cost_usd"],
        unpriced=bool(row["unpriced"]),
        error=row["error"],
    )


def save_intent(store: Store, intent: Intent) -> None:
    store.execute(
        "INSERT OR REPLACE INTO intents (gesture_id, tenant, act, object, system, page,"
        " values_seen, continues, confidence, why, model, in_tokens, out_tokens,"
        " cost_usd, unpriced, created_at, error)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            intent.gesture_id,
            intent.tenant,
            intent.act,
            intent.object,
            intent.system,
            intent.page,
            json.dumps([asdict(seen) for seen in intent.values_seen]),
            intent.continues,
            intent.confidence,
            intent.why,
            intent.model,
            intent.in_tokens,
            intent.out_tokens,
            intent.cost_usd,
            int(intent.unpriced),
            _now(),
            intent.error,
        ),
    )


def tail_for(store: Store, stream_id: str, before: float) -> list[Intent]:
    rows = store.query(
        "SELECT i.* FROM intents i JOIN gestures g ON g.id = i.gesture_id"
        " WHERE g.stream_id = ? AND g.at < ? ORDER BY g.at DESC LIMIT 8",
        (stream_id, before),
    )
    return list(reversed([_row_to_intent(row) for row in rows]))


# One reading loop at a time. Two concurrent callers both SELECT the same
# unread gestures before either writes an intent, so every gesture in the race
# window is asked -- and billed -- twice, while INSERT OR REPLACE leaves only
# one cost row. `read_on_ingest` fires one of these per ingest, so two batches
# arriving together is enough to trigger it.
# ponytail: a process-local lock, because the rig is one process. Claim rows in
# the database if it ever becomes more than one.
_reading = asyncio.Lock()


async def read_new_gestures(store: Store, asker: Asker, model: str) -> int:
    """Every stored gesture with no intent gets exactly one reading."""
    async with _reading:
        return await _read_unread(store, asker, model)


async def _read_unread(store: Store, asker: Asker, model: str) -> int:
    rows = store.query(
        "SELECT g.* FROM gestures g LEFT JOIN intents i ON i.gesture_id = g.id"
        " WHERE i.gesture_id IS NULL ORDER BY g.at LIMIT 200"
    )

    written = 0
    for row in rows:
        gesture = _row_to_gesture(row)
        intent = await read_gesture(
            gesture,
            tail=tail_for(store, gesture.stream_id, gesture.at),
            asker=asker,
            model=model,
        )
        save_intent(store, intent)
        written += 1
    return written


def build_app(
    *,
    store: Store,
    asker: Asker,
    token: str,
    tenant: str,
    read_on_ingest: bool = True,
) -> FastAPI:
    """read_on_ingest=False in tests: a background reading task racing the
    assertions makes every ingest test depend on scheduling."""
    app = FastAPI(title="rig")
    app.state.store = store
    app.state.asker = asker
    app.state.token = token
    app.state.tenant = tenant

    def authorised(authorization: Annotated[str | None, Header()] = None) -> None:
        if authorization != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="the rig did not accept that token")

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/observations", status_code=202, dependencies=[Depends(authorised)])
    async def observations(raw: dict[str, Any]) -> dict[str, Any]:
        # Not `batch: Batch`. FastAPI would validate the whole envelope at once,
        # and one unrecognised event -- a gesture kind the extension shipped
        # last week -- would fail the request and lose every good event beside
        # it. The protocol is explicit that a rejected event does not reject the
        # batch, so the events are parsed one at a time.
        #
        # The cost of taking a raw dict is that FastAPI no longer answers a
        # malformed envelope with a 422 of its own, so this does. A bad event is
        # tolerated; a bad batch is still refused, and refused with the status
        # the caller can act on.
        try:
            batch, rejected = parse_batch(raw)
        except ValidationError as problem:
            # include_input=False: parse_batch() rebuilds the envelope with
            # already-parsed Event objects before this validation runs, so
            # problem.errors()'s default 'input' can hold a pydantic model
            # instance rather than plain JSON -- which blows up the response
            # this except exists to send, turning the intended 422 into a 500.
            raise HTTPException(
                status_code=422, detail=problem.errors(include_input=False)
            ) from problem
        accepted, already = save_batch(store, batch, tenant, rejected=len(rejected))
        if read_on_ingest and not already:
            asyncio.create_task(_read_soon(store, asker))
        return {
            "batch_id": batch.batch_id,
            "accepted": accepted,
            "rejected": len(rejected),
            "problems": [{"index": r.index, "reason": r.reason} for r in rejected],
            "already_had_it": already,
        }

    @app.post("/v1/observations/artifacts", status_code=201, dependencies=[Depends(authorised)])
    async def artifact(
        batch_id: Annotated[str, Form()],
        kind: Annotated[str, Form()],
        file: UploadFile,
        frame_index: Annotated[int | None, Form()] = None,
    ) -> dict[str, Any]:
        root = (settings().db_path.parent / "artifacts").resolve()
        blob = (root / batch_id).resolve()
        if not blob.is_relative_to(root):
            # batch_id arrives on a form field. "../../evil" wrote outside the
            # artifacts directory entirely -- checked on the resolved path
            # rather than by blacklisting characters, which is the check that
            # actually holds.
            raise HTTPException(status_code=400, detail="batch_id is not a usable name")
        blob.mkdir(parents=True, exist_ok=True)
        name = f"{kind}-{frame_index if frame_index is not None else 'x'}.png"
        data = await file.read()
        (blob / name).write_bytes(data)
        return {"uri": str(blob / name), "size_bytes": len(data)}

    return app


async def _read_soon(store: Store, asker: Asker) -> None:
    try:
        await read_new_gestures(store, asker, settings().intent_model)
    except Exception:  # noqa: BLE001, S110 -- a reading loop must not take the process with it
        pass


def _default_app() -> FastAPI:
    config = settings()
    store = Store(config.db_path)
    store.migrate()
    asker = GeminiAsker(config.gemini_api_key) if config.gemini_api_key else None
    if asker is None:
        raise RuntimeError("set RIG_GEMINI_API_KEY")
    return build_app(store=store, asker=asker, token=config.ingest_token, tenant=config.tenant)


app = _default_app() if settings().gemini_api_key else FastAPI(title="rig (no key)")
