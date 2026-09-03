"""The rig's one process: take what the extension saw, read it, show it."""

import asyncio
import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
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
    # Pure -- fine to call before the transaction below.
    gestures, orphan_requests, orphan_pages = correlate(batch, tenant)

    # One transaction for the claim and the writes. A batch id claimed by the
    # INSERT below but never followed by its gestures -- because something
    # after it raised -- is an id that can never be retried: the events it
    # named are gone, but the id says they were already handled. Doing the
    # claim and the writes in the same `with` means any exception in the
    # block rolls the claim back too, so a retry with the same batch_id sees
    # no row and tries again for real. sqlite3's connection context manager
    # commits on a clean exit and rolls back on any exception, IntegrityError
    # from the duplicate-batch_id case included.
    try:
        with store.connect() as connection:
            connection.execute(
                "INSERT INTO batches (batch_id, device_id, tenant, mode, received_at,"
                " accepted, rejected) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    batch.batch_id,
                    batch.device_id,
                    tenant,
                    batch.mode,
                    _now(),
                    len(gestures),
                    rejected,
                ),
            )
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
    except sqlite3.IntegrityError:
        return 0, True

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

# read_new_gestures reads at most 200 rows per pass; a drain must call it
# repeatedly. Bounded because every pass must reduce the unread set: a pass
# that returns 0 ends it, and this cap is a backstop against a row that
# cannot be read and would otherwise spin. 200 x 100 = 20,000 gestures in one
# drain, far beyond any real batch.
MAX_READING_PASSES = 100


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


def _target_name(target: dict[str, Any] | None) -> str | None:
    """What to call the control a gesture touched, or nothing.

    A scroll has no target at all -- you scroll a page, not an element -- so
    this must survive None. Real capture is about 15% scrolls, and the previous
    version took the whole route down for any stream containing one.
    """
    if not target:
        return None
    return target.get("name") or (target.get("component") or {}).get("fieldLabel")


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

    @app.get("/v1/streams", dependencies=[Depends(authorised)])
    def streams() -> dict[str, Any]:
        rows = store.query(
            "SELECT stream_id, count(*) AS gestures, min(at) AS first, max(at) AS last"
            " FROM gestures GROUP BY stream_id ORDER BY last DESC"
        )
        return {"streams": [dict(row) for row in rows]}

    @app.get("/v1/gestures", dependencies=[Depends(authorised)])
    def gestures(stream: str | None = None, limit: int = 200) -> dict[str, Any]:
        limit = max(1, min(limit, 1000))  # the page polls; an unbounded limit is a footgun
        sql = (
            "SELECT g.id, g.stream_id, g.at, g.url, g.system, g.gesture_json,"
            " g.requests, i.act, i.object, i.page, i.confidence, i.why, i.values_seen,"
            " i.cost_usd, i.error"
            " FROM gestures g LEFT JOIN intents i ON i.gesture_id = g.id"
        )
        params: tuple[Any, ...] = ()
        if stream:
            sql += " WHERE g.stream_id = ?"
            params = (stream,)
        sql += " ORDER BY g.at LIMIT ?"
        params = (*params, limit)

        out = []
        for row in store.query(sql, params):
            wire = json.loads(row["gesture_json"])
            out.append(
                {
                    "id": row["id"],
                    "at": row["at"],
                    "url": row["url"],
                    "system": row["system"],
                    "kind": wire["kind"],
                    # A scroll carries no target at all -- you scroll a page,
                    # not an element -- and .get() on None takes the whole route
                    # down for any stream containing one. That is 15% of real
                    # gestures in the acme sample.
                    "target": _target_name(wire.get("target")),
                    "calls": len(json.loads(row["requests"])),
                    "intent": None
                    if row["act"] is None and row["error"] is None
                    else {
                        "act": row["act"],
                        "object": row["object"],
                        "page": row["page"],
                        "confidence": row["confidence"],
                        "why": row["why"],
                        "values_seen": json.loads(row["values_seen"] or "[]"),
                        "cost_usd": row["cost_usd"],
                        "error": row["error"],
                    },
                }
            )
        return {"gestures": out}

    @app.get("/v1/spend", dependencies=[Depends(authorised)])
    def spend() -> dict[str, Any]:
        row = store.query(
            "SELECT count(*) AS n, coalesce(sum(in_tokens), 0) AS i,"
            " coalesce(sum(out_tokens), 0) AS o, coalesce(sum(cost_usd), 0.0) AS c,"
            " coalesce(sum(unpriced), 0) AS u"
            " FROM intents"
        )[0]
        gestures_total = store.query("SELECT count(*) AS n FROM gestures")[0]["n"]
        return {
            "gestures": gestures_total,
            "gestures_read": row["n"],
            "in_tokens": row["i"],
            "out_tokens": row["o"],
            "cost_usd": round(row["c"], 6),
            # Readings whose cost we could not establish. A total that ignores
            # these understates the bill and says nothing about it.
            "unpriced": row["u"],
            "per_gesture_usd": round(row["c"] / row["n"], 8) if row["n"] else 0.0,
        }

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return (Path(__file__).parent / "web" / "index.html").read_text()

    return app


async def _read_soon(store: Store, asker: Asker) -> None:
    try:
        # Drain, do not take one page. read_new_gestures reads at most 200 and
        # fires once per batch, while a single upload can carry 500 gestures --
        # so the remainder waited for another batch that may never come. When
        # capture stops for the day, those readings never happen at all.
        # Bounded because every pass must reduce the unread set: a pass that
        # returns 0 ends it, and the cap is a backstop against a row that
        # cannot be read and would otherwise spin.
        for _ in range(MAX_READING_PASSES):
            if not await read_new_gestures(store, asker, settings().intent_model):
                return
    except Exception:  # noqa: BLE001, S110 -- a reading loop must not take the process with it
        pass


def _default_app() -> FastAPI:
    config = settings()
    store = Store(config.db_path)
    store.migrate()
    asker = GeminiAsker(config.gemini_api_key)
    return build_app(store=store, asker=asker, token=config.ingest_token, tenant=config.tenant)


def _refuse_to_start() -> FastAPI:
    """No RIG_GEMINI_API_KEY. Refusing at ASGI startup -- not at import --
    keeps `from rig.api import build_app` (every test's import, and every
    other module that imports this one) safe, and refusing per-request would
    just 404 forever instead of ever saying the one thing the operator needs
    to hear. `make serve` with no key now fails loudly, once, before the
    first request is served, naming the variable to set.
    """

    @asynccontextmanager
    async def refuse(_: FastAPI) -> AsyncIterator[None]:
        raise RuntimeError("set RIG_GEMINI_API_KEY")
        yield  # pragma: no cover -- unreachable, but a lifespan must be a generator

    return FastAPI(title="rig (no key)", lifespan=refuse)


app = _default_app() if settings().gemini_api_key else _refuse_to_start()
