"""The rig's one process: take what the extension saw, read it, show it."""

import asyncio
import json
import logging
import sqlite3
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    Depends,
    FastAPI,
    Form,
    Header,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from rig.channel import DeviceChannel, DeviceUnreachable
from rig.config import settings
from rig.correlate import correlate
from rig.intents import read_gesture
from rig.models import Asker, GeminiAsker, one_at_a_time
from rig.records import Gesture, Intent, ValueSeen
from rig.store import Store
from rig.wire import Batch, PageEvent, Request, parse_batch
from rig.wire import Gesture as WireGesture

# uvicorn configures the root logger, so this reaches the same place every
# other line the operator watches does. The rig had no logging at all; a
# reading loop that dies is the one event that must not be inferred from
# silence -- see service-worker.js:422, the same system making the opposite
# choice.
log = logging.getLogger("rig")

K_ABORT_DEADLINE_S = 2.0
"""How long the stop button waits on the browser. The flag is what stops the
run; this command only saves the extension a step it is mid-way through, and a
person pressing stop is owed an answer sooner than a command deadline."""


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def save_batch(store: Store, batch: Batch, tenant: str, rejected: int = 0) -> tuple[int, bool, int]:
    """Store one batch and its gestures. Idempotent on batch_id.

    Returns (accepted, already_had_it, snapshots_ignored).
    """
    # Pure -- fine to call before the transaction below.
    gestures, orphan_requests, orphan_pages, snapshots_ignored = correlate(batch, tenant)

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
                "INSERT INTO batches (batch_id, device_id, tenant, mode, started_at,"
                " ended_at, recording_id, received_at, accepted, rejected)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    batch.batch_id,
                    batch.device_id,
                    tenant,
                    batch.mode,
                    batch.started_at,
                    batch.ended_at,
                    batch.recording_id,
                    _now(),
                    len(gestures),
                    rejected,
                ),
            )
            for gesture in gestures:
                connection.execute(
                    "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, url, system,"
                    " tab_id, frame_url, page_url, gesture_json, requests, page_events)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                        gesture.page_url,
                        gesture.gesture.model_dump_json(),
                        json.dumps(
                            [r.model_dump(mode="json") for r in gesture.requests],
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            [p.model_dump(mode="json") for p in gesture.page_events],
                            ensure_ascii=False,
                        ),
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
                # No dedup key here on purpose: two distinct page events can
                # share (batch_id, at, payload), and the surrogate id in the
                # schema means every row is kept -- batch_id's own PRIMARY KEY
                # on `batches` above already makes re-ingesting a batch a no-op.
                connection.execute(
                    "INSERT INTO orphan_pages (batch_id, tenant, at, payload) VALUES (?, ?, ?, ?)",
                    (batch.batch_id, tenant, page.at, page.model_dump_json()),
                )
    except sqlite3.IntegrityError as problem:
        # Only the duplicate batch_id is "we already had this". Every other
        # integrity failure in the block -- a gesture id already stored, some
        # constraint added later -- was answered the same way, and the answer
        # tells the extension the batch was handled: it drops those events and
        # never retries, so they are gone. Silent, unrecoverable, and the whole
        # difference between "already stored" and "stored nothing".
        #
        # Matched on the message because sqlite3 reports no code for WHICH
        # constraint failed -- sqlite3.IntegrityError has one errno for all of
        # them. A rename of the table or column changes this string, which is
        # why the case it covers is the one the tests construct.
        if "batches.batch_id" not in str(problem):
            raise
        return 0, True, 0

    return len(gestures), False, snapshots_ignored


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
        page_url=row["page_url"],
        gesture=WireGesture.model_validate_json(row["gesture_json"]),
        requests=[Request.model_validate(r) for r in json.loads(row["requests"])],
        page_events=[PageEvent.model_validate(p) for p in json.loads(row["page_events"])],
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
        thought_tokens=row["thought_tokens"],
        cost_usd=row["cost_usd"],
        unpriced=bool(row["unpriced"]),
        error=row["error"],
    )


def save_intent(store: Store, intent: Intent) -> None:
    store.execute(
        "INSERT OR REPLACE INTO intents (gesture_id, tenant, act, object, system, page,"
        " values_seen, continues, confidence, why, model, in_tokens, out_tokens,"
        " thought_tokens, cost_usd, unpriced, created_at, error)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            intent.gesture_id,
            intent.tenant,
            intent.act,
            intent.object,
            intent.system,
            intent.page,
            json.dumps([asdict(seen) for seen in intent.values_seen], ensure_ascii=False),
            intent.continues,
            intent.confidence,
            intent.why,
            intent.model,
            intent.in_tokens,
            intent.out_tokens,
            intent.thought_tokens,
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


# read_new_gestures reads at most 200 rows per pass; a drain must call it
# repeatedly. Bounded because every pass must reduce the unread set: a pass
# that returns 0 ends it, and this cap is a backstop against a row that
# cannot be read and would otherwise spin. 200 x 100 = 20,000 gestures in one
# drain, far beyond any real batch.
MAX_READING_PASSES = 100


async def read_new_gestures(store: Store, asker: Asker, model: str, tenant: str) -> int:
    """Every stored gesture of THIS TENANT with no intent gets exactly one reading.

    Scoped, because the reading is what costs money: a second tenant in one
    store had this loop paying for gestures no pass of ours will ever mine, and
    filing intents under their tenant on our bill.

    One reading loop at a time. Two concurrent callers both SELECT the same
    unread gestures before either writes an intent, so every gesture in the
    race window is asked -- and billed -- twice, while INSERT OR REPLACE leaves
    only one cost row. `read_on_ingest` fires one of these per ingest, so two
    batches arriving together is enough to trigger it.

    ponytail: a process-local lock, because the rig is one process. Claim rows
    in the database if it ever becomes more than one.
    """
    async with one_at_a_time("reading"):
        return await _read_unread(store, asker, model, tenant)


async def _read_unread(store: Store, asker: Asker, model: str, tenant: str) -> int:
    # An intent row means a reading happened, whatever came back in it -- an
    # error, or an answer whose `act` was the wrong type and got nulled. None
    # of those is retried: the model was asked, it answered, and it was billed.
    # Re-asking the same evidence with the same prompt bills again for the same
    # likely answer. What a row with no usable `act` gets instead is to be
    # visible: /v1/spend counts it in `unusable`, /v1/gestures returns an
    # intent rather than null, and the page says so. Not both billed and
    # hidden -- pick one, and this picks visible.
    rows = store.query(
        "SELECT g.* FROM gestures g LEFT JOIN intents i ON i.gesture_id = g.id"
        " WHERE i.gesture_id IS NULL AND g.tenant = ? ORDER BY g.at LIMIT 200",
        (tenant,),
    )

    cap = settings().daily_usd_cap
    if cap >= 0:
        since = datetime.now(tz=UTC).date().isoformat()
        # The unpriced count is read beside the sum, and stops the day just as
        # hard. A cap that trusts SUM(cost_usd) alone is blind to the one
        # failure PRICES cannot fix: a model name the table never knew about
        # records $0.0000 with unpriced=1, so an unattended week on a new
        # preview name spends without limit while the guard reads zero. This
        # deployment already lived that once -- the run that proved the
        # architecture billed $1.12 and every row said free.
        today = store.query(
            "SELECT COALESCE(SUM(cost_usd), 0.0) AS usd,"
            " COALESCE(SUM(unpriced), 0) AS blind FROM intents"
            " WHERE tenant = ? AND created_at >= ?",
            (tenant, since),
        )[0]
        spent, blind = today["usd"], today["blind"]
        if spent >= cap or blind:
            # Reading stops; capture does not. The evidence is still stored, so
            # raising the cap tomorrow reads what today declined -- which is why
            # this stops the asking rather than the mirroring.
            log.warning(
                "daily cap reached for %s: $%.4f of $%.2f, %d unpriced reading(s),"
                " %d gesture(s) unread",
                tenant,
                spent,
                cap,
                blind,
                len(rows),
            )
            return 0

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
    app.state.channel = DeviceChannel(deadline_s=settings().command_deadline_s)

    def authorised(authorization: Annotated[str | None, Header()] = None) -> None:
        if authorization != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="the rig did not accept that token")

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/v1/agents/{device_id}/commands")
    async def commands(websocket: WebSocket, device_id: str) -> None:
        """The extension dials this the way it dials the backend's.

        The credential rides in the subprotocol, not the query string: a
        browser cannot set a header on a WebSocket, and a token in the URL is
        a token in every access log. The rig has one token and no device
        secret -- this is a development second reader, and the boundary is
        that whoever holds the ingest token may drive a browser that has
        chosen to dial here. Refused sockets close with 1008 exactly like a
        wrong token would, so the handshake enumerates nothing.
        """
        protocols = [
            part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")
        ]
        offered = protocols[1] if len(protocols) > 1 and protocols[0] == "bearer" else ""
        if offered != token:
            await websocket.close(code=1008)
            return
        await websocket.accept(subprotocol="bearer")
        channel: DeviceChannel = app.state.channel
        channel.attach(device_id, websocket)
        log.info("device %s connected to the rig", device_id)
        try:
            while True:
                # Named by the route, not by the message: a browser that told
                # the registry which device it was could say it was another.
                channel.deliver(await websocket.receive_text(), device_id)
        except WebSocketDisconnect:
            pass
        finally:
            channel.detach(device_id, websocket)
            log.info("device %s disconnected from the rig", device_id)

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
        accepted, already, snapshots_ignored = save_batch(
            store, batch, tenant, rejected=len(rejected)
        )
        if read_on_ingest and not already:
            _spawn_reading(store, asker, tenant)
        return {
            "batch_id": batch.batch_id,
            "accepted": accepted,
            "rejected": len(rejected),
            "problems": [{"index": r.index, "reason": r.reason} for r in rejected],
            "already_had_it": already,
            "snapshots_ignored": snapshots_ignored,
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
        name = f"{kind}-{frame_index if frame_index is not None else 'x'}.png"
        target = (blob / name).resolve()
        if not target.is_relative_to(root):
            # `kind` is a form field too, and it was interpolated into the name
            # with nothing checking it -- so the check above held for batch_id
            # while its sibling wrote anywhere this process can reach. Proved:
            # kind="../../..{tmp}/x" answered 201 and left the bytes there.
            # The check belongs on the path actually written rather than on the
            # directory, because a directory that is inside the root says
            # nothing about a name that climbs back out of it.
            raise HTTPException(status_code=400, detail="kind is not a usable name")
        blob.mkdir(parents=True, exist_ok=True)
        data = await file.read()
        target.write_bytes(data)
        return {"uri": str(target), "size_bytes": len(data)}

    @app.get("/v1/streams", dependencies=[Depends(authorised)])
    def streams() -> dict[str, Any]:
        rows = store.query(
            "SELECT stream_id, count(*) AS gestures, min(at) AS first, max(at) AS last"
            " FROM gestures WHERE tenant = ? GROUP BY stream_id ORDER BY last DESC",
            (tenant,),
        )
        return {"streams": [dict(row) for row in rows]}

    @app.get("/v1/gestures", dependencies=[Depends(authorised)])
    def gestures(stream: str | None = None, limit: int = 200) -> dict[str, Any]:
        limit = max(1, min(limit, 1000))  # the page polls; an unbounded limit is a footgun
        sql = (
            "SELECT g.id, g.stream_id, g.at, g.url, g.system, g.gesture_json,"
            " g.requests, i.gesture_id AS read_id, i.act, i.object, i.page,"
            " i.confidence, i.why, i.values_seen, i.cost_usd, i.unpriced, i.error"
            " FROM gestures g LEFT JOIN intents i ON i.gesture_id = g.id"
            " WHERE g.tenant = ?"
        )
        params: tuple[Any, ...] = (tenant,)
        if stream:
            sql += " AND g.stream_id = ?"
            params = (*params, stream)
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
                    # `read_id` is i.gesture_id: NULL only when the LEFT
                    # JOIN found no intent at all. The test used to be
                    # `act is None and error is None`, two of seventeen
                    # columns, so a reading that was made and billed but came
                    # back with an unusable `act` was served as null -- the
                    # page said "not read yet" while /v1/spend counted it read,
                    # and `why`, `confidence` and `cost_usd` were dropped from
                    # the view. Every reading that happened is now reported as
                    # one; `act` may be null inside it, and that is the thing
                    # the reader is entitled to see.
                    "intent": None
                    if row["read_id"] is None
                    else {
                        "act": row["act"],
                        "object": row["object"],
                        "page": row["page"],
                        "confidence": row["confidence"],
                        "why": row["why"],
                        # No `or "[]"`: this arm is only evaluated when the
                        # LEFT JOIN found an intent row, and `values_seen` is
                        # NOT NULL DEFAULT '[]' with save_intent as its only
                        # writer -- there is no way for it to arrive NULL.
                        "values_seen": json.loads(row["values_seen"]),
                        "cost_usd": row["cost_usd"],
                        # A $0.00 row and an honestly-unpriced row are
                        # identical in cost_usd alone. The page draws the
                        # difference; it could not until this was sent.
                        "unpriced": bool(row["unpriced"]),
                        "error": row["error"],
                    },
                }
            )
        return {"gestures": out}

    @app.get("/v1/spend", dependencies=[Depends(authorised)])
    def spend() -> dict[str, Any]:
        row = store.query(
            "SELECT count(*) AS n, coalesce(sum(in_tokens), 0) AS i,"
            " coalesce(sum(out_tokens), 0) AS o, coalesce(sum(thought_tokens), 0) AS t,"
            " coalesce(sum(cost_usd), 0.0) AS c,"
            " coalesce(sum(unpriced), 0) AS u,"
            " coalesce(sum(act IS NULL AND error IS NULL), 0) AS x"
            " FROM intents WHERE tenant = ?",
            (tenant,),
        )[0]
        gestures_total = store.query(
            "SELECT count(*) AS n FROM gestures WHERE tenant = ?", (tenant,)
        )[0]["n"]
        # Summed where the cost actually lives. One pass is one model call over
        # the whole day, so its bill is one row -- and the workflows it found
        # each carrying a copy of that figure is how SUM over workflows came to
        # overstate the total by the number of jobs found.
        mining = store.query(
            "SELECT count(*) AS n, coalesce(sum(cost_usd), 0.0) AS c,"
            " coalesce(sum(unpriced), 0) AS u,"
            " coalesce(sum(thought_tokens), 0) AS t FROM passes WHERE tenant = ?",
            (tenant,),
        )[0]
        return {
            "passes": mining["n"],
            "mining_usd": round(mining["c"], 6),
            "mining_unpriced": mining["u"],
            "gestures": gestures_total,
            "gestures_read": row["n"],
            "in_tokens": row["i"],
            "out_tokens": row["o"],
            # Inside out_tokens, billed at the output rate, and on Flash about
            # 84% of it. Answer.thought_tokens reached no reader at all: the
            # bill said the readings were expensive and nothing said that most
            # of what was paid for was reasoning nobody ever read.
            "thought_tokens": row["t"] + mining["t"],
            "cost_usd": round(row["c"], 6),
            # Readings whose cost we could not establish. A total that ignores
            # these understates the bill and says nothing about it.
            "unpriced": row["u"],
            # Readings that happened, cost money, and produced no act. Counted
            # in gestures_read because they were read -- but a header saying
            # "7/7 read" when three of them are empty is the console lying by
            # omission, which is the same defect as `unpriced` one field over.
            "unusable": row["x"],
            # Divided by readings, not by gestures: a gesture nobody has read
            # yet has cost nothing, and averaging over it says the model is
            # getting cheaper as the backlog grows. The console's label used to
            # say "a gesture" over this arithmetic; the label was the wrong
            # half and now reads "a reading".
            "per_gesture_usd": round(row["c"] / row["n"], 8) if row["n"] else 0.0,
        }

    @app.post("/v1/mine", dependencies=[Depends(authorised)])
    async def run_a_pass() -> dict[str, Any]:
        from rig.mine import mine

        result = await mine(store, tenant=tenant, asker=asker, model=settings().mine_model)
        return {
            # The row in `passes` this reading wrote. Every workflow below
            # names it, and it is where the pass's bill lives.
            "pass_id": result.pass_id,
            # A refused or failed call reaches here as an Answer carrying a
            # reason and no data. Dropped, it left a pass that found nothing
            # looking exactly like a pass that had nothing to find.
            "error": result.error,
            "proposed": result.proposed,
            "kept": result.kept,
            "window": result.window_size,
            # Evidence the pass did not read. `left_out` did not fit the token
            # budget and is offered again next pass; `lost_pool` is a pooled id
            # with no gesture row, which no pass can ever read. Neither is
            # inferable from `window` alone.
            "left_out": result.left_out,
            "lost_pool": result.lost_pool,
            "rejections": [
                {"title": r.workflow_title, "reason": r.reason, "detail": r.detail}
                for r in result.rejections
            ],
            # A workflow that was proposed, passed every check and was still
            # not kept was resolved onto one already stored. Without this,
            # `proposed: 3, kept: 0, rejections: []` is three jobs that
            # vanished with no account of where they went.
            "resolutions": [
                {
                    "kind": r.kind,
                    "workflow_id": r.workflow_id,
                    "score": r.score,
                    "contains": r.contains,
                }
                for r in result.resolutions
            ],
            "coverage": {
                "coverage": result.coverage.coverage,
                "skew": result.coverage.skew,
                "gini": result.coverage.gini,
                # Which of the two numbers beside it broke its threshold is
                # readable from them; that one did is the verdict.
                "lopsided": result.lopsided,
            },
            "in_tokens": result.in_tokens,
            "out_tokens": result.out_tokens,
            "cost_usd": round(result.cost_usd, 6),
            "unpriced": result.unpriced,
        }

    @app.get("/v1/pool", dependencies=[Depends(authorised)])
    def pool() -> dict[str, Any]:
        """What the next pass will be offered first, and what it will not.

        `retired` is the record pool.py says must exist: evidence that stopped
        being privileged, when it entered and under which cap it aged out.
        Nothing over the wire could read it, so a pass whose window quietly
        stopped carrying yesterday's tail looked exactly like one that had
        nothing left to carry. Retired is not gone -- it is packed again as
        ordinary evidence, at its own strength.
        """
        from rig.pool import pool_ids, retired_entries

        return {
            "pooled": pool_ids(store, tenant),
            "retired": [asdict(entry) for entry in retired_entries(store, tenant)],
        }

    @app.get("/v1/workflows", dependencies=[Depends(authorised)])
    def workflows() -> dict[str, Any]:
        from rig.workflows import known_workflows

        return {
            "workflows": [
                {
                    "id": w.id,
                    "title": w.title,
                    "narrative": w.narrative,
                    "systems": w.systems,
                    # The pass that found it, rather than a per-workflow price.
                    # One call proposes every workflow in a pass, so a copy of
                    # its cost on each of them summed to the bill times the
                    # number of jobs found. Ask `passes` for what it cost.
                    "pass_id": w.pass_id,
                    # `parameters` and `unproven` are the workflow's own model
                    # output and exist nowhere a reader can reach but here --
                    # `unproven` in particular is what the pass could not place,
                    # which is the one thing a reader most needs and the field a
                    # route that emits its siblings is likeliest to drop.
                    "parameters": w.parameters,
                    "unproven": w.unproven,
                    "steps": [
                        {
                            "order": s.order,
                            "says": s.says,
                            "system": s.system,
                            "cites": s.cites,
                            "parameters": s.parameters,
                        }
                        for s in w.steps
                    ],
                }
                for w in known_workflows(store, tenant)
            ]
        }

    @app.get("/v1/workflows/{workflow_id}/evidence", dependencies=[Depends(authorised)])
    def workflow_evidence(workflow_id: str) -> dict[str, Any]:
        """Everything a workflow cites, in the shape a runner's bridge consumes.

        `/v1/workflows` serves the prose and the citations; `/v1/gestures`
        reduces a target to its NAME, for a person reading a listing. Between
        them, nothing served the target itself -- so the backend's
        `application.skill.from_rig`, whose whole purpose is turning a mined
        step into something replayable, had no route to read and had to be
        pointed at the `gestures.gesture_json` column. A bridge that can only
        be used by something with the rig's SQLite file is not a bridge.

        Cited gestures only, not the stream and not the store. A workflow is a
        claim about specific evidence, and this is that evidence: the largest
        real workflow cites 35 of 387 gestures.

        `requests` is served beside the gestures rather than folded into them,
        because that is how the two are stored and how the bridge takes them --
        one map keyed by gesture id each. `recordings` is the distinct capture
        streams those gestures arrived on, which is the one input the caller
        would otherwise have to reach into a column for; the backend needs it
        for `Provenance`, and getting it wrong there mis-states whether a
        skill's values were ever diffed.

        Complete rather than trimmed, and the cost is known: measured over the
        real store, response bodies are 94% of the 7.2 MB of captured requests,
        and the bridge reads none of them today -- it takes a status and a
        request body. Serving them anyway, because the next consumer is
        assertions: a write that proves nothing about its result is a live
        concern in the skill domain (`unchecked_writes`), post-conditions are
        built from responses, and a route called `evidence` that quietly ships
        6% of the evidence is the shape of defect this project keeps finding.
        The largest single workflow comes to 1.6 MB and all eight to 3.4 MB,
        which is nothing for one internal fetch per job.
        """
        from rig.workflows import known_workflows

        found = next((w for w in known_workflows(store, tenant) if w.id == workflow_id), None)
        if found is None:
            raise HTTPException(status_code=404, detail="no such workflow")

        cited = list(dict.fromkeys(gid for step in found.steps for gid in step.cites))
        gestures: dict[str, Any] = {}
        requests: dict[str, Any] = {}
        streams: list[str] = []
        if cited:
            marks = ",".join("?" * len(cited))
            rows = store.query(
                "SELECT id, stream_id, gesture_json, requests FROM gestures"
                f" WHERE tenant = ? AND id IN ({marks}) ORDER BY at",
                (tenant, *cited),
            )
            for row in rows:
                gestures[row["id"]] = json.loads(row["gesture_json"])
                requests[row["id"]] = json.loads(row["requests"])
                if row["stream_id"] not in streams:
                    streams.append(row["stream_id"])

        # A citation naming evidence this store no longer holds is reported
        # rather than dropped. `validate` refuses a proposal citing a gesture
        # that does not exist, so reaching this with one means the store moved
        # after the workflow was kept -- and a caller building a runnable job
        # out of it is entitled to know its evidence is incomplete before it
        # builds a version that silently misses a step.
        return {
            "workflow_id": workflow_id,
            "gestures": gestures,
            "requests": requests,
            "recordings": streams,
            "missing": [gid for gid in cited if gid not in gestures],
        }

    @app.get("/v1/devices", dependencies=[Depends(authorised)])
    def devices() -> dict[str, Any]:
        return {"devices": app.state.channel.online()}

    @app.post("/v1/runs", status_code=202, dependencies=[Depends(authorised)])
    async def start_run(body: dict[str, Any]) -> dict[str, Any]:
        """The press. A person opened a door and chose live or dry; the rig
        has no way to start a run on its own."""
        from rig.runner import run_workflow
        from rig.runs import Run, new_run_id, save_run
        from rig.workflows import known_workflows

        # The browser first, then the workflow: "your browser is not connected"
        # is the answer a person can act on, and it holds whatever they asked
        # for. A device that is merely busy is refused before the workflow is
        # looked up for the same reason.
        device_id = str(body.get("device_id") or "")
        if device_id not in app.state.channel.online():
            raise HTTPException(
                status_code=409, detail=f"{device_id or 'no device'} is not connected to the rig"
            )
        # One browser, one hand. Two runs driving the same window interleave
        # their clicks into a form neither of them can then read back.
        # ponytail: a read-then-write, not a cross-worker lock -- sound because
        # the rig runs one uvicorn worker, which the in-process channel and
        # `Aborts` already require. A second worker needs a UNIQUE partial index
        # on (tenant, device_id) where outcome = 'running'.
        busy = store.query(
            "SELECT id FROM runs WHERE tenant = ? AND device_id = ? AND outcome = 'running'"
            " ORDER BY started_at LIMIT 1",
            (tenant, device_id),
        )
        if busy:
            raise HTTPException(
                status_code=409, detail=f"{device_id} is already running {busy[0]['id']}"
            )
        workflow = next(
            (w for w in known_workflows(store, tenant) if w.id == body.get("workflow_id")), None
        )
        if workflow is None:
            raise HTTPException(status_code=404, detail="no such workflow")
        # The caller's body is the only source of values. Nothing the chat door
        # understood is carried across on its own -- the press is what says
        # which values this run is performed with. Coerced values, not checked
        # ones, would turn `{"clientCode": {...}}` into the string "{...}" and
        # type it into somebody's form.
        given = body.get("values", {})
        if not isinstance(given, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in given.items()
        ):
            raise HTTPException(status_code=400, detail="values must be an object of strings")
        values: dict[str, str] = given
        # Every parameter the workflow declares must arrive with a value. The
        # planner falls back to the value the recording happened to contain when
        # a step has none -- right for a step nobody parameterised, and for a
        # declared parameter left blank it would quietly perform the job with
        # somebody else's client code. Named, never echoed: a refusal that
        # quotes the values is a refusal in the access log.
        absent = sorted(
            str(p["name"])
            for p in workflow.parameters
            if isinstance(p, dict) and p.get("name") and str(p["name"]) not in values
        )
        if absent:
            raise HTTPException(
                status_code=400, detail=f"this job needs a value for: {', '.join(absent)}"
            )

        # Claimed here, not by the task. Written inside `run_workflow`, the
        # `running` row appears only once the spawned task gets its first slice,
        # and a second press arriving in that window reads no busy run and puts
        # a second hand on the same browser.
        run_id = new_run_id()
        save_run(
            store,
            Run(
                id=run_id,
                tenant=workflow.tenant,
                workflow_id=workflow.id,
                device_id=device_id,
                values=values,
                started_by=str(body.get("started_by") or "form"),
                # Dry unless a person said otherwise. A missing `live` is not a
                # caller who forgot; it is the default this system promises.
                live=bool(body.get("live")),
                allow_focus=bool(body.get("allow_focus", True)),
                started_at=_now(),
            ),
        )
        _spawn_run(
            run_workflow(
                store,
                workflow,
                values=values,
                channel=app.state.channel,
                device_id=device_id,
                asker=app.state.asker,
                plan_model=settings().plan_model,
                rescue_model=settings().rescue_model,
                live=bool(body.get("live")),
                allow_focus=bool(body.get("allow_focus", True)),
                started_by=str(body.get("started_by") or "form"),
                run_id=run_id,
            )
        )
        return {"run_id": run_id}

    @app.get("/v1/runs/{run_id}", dependencies=[Depends(authorised)])
    def read_run(run_id: str) -> dict[str, Any]:
        from rig.runs import as_json, load_run

        run = load_run(store, tenant, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="no such run")
        return as_json(run)

    @app.post("/v1/runs/{run_id}/abort", dependencies=[Depends(authorised)])
    async def abort_run(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
        from rig.runner import Aborts

        # The flag first, then the browser: the loop checks it between steps,
        # and a device that has gone away must not stop the run from being
        # marked aborted.
        Aborts.abort(run_id)
        device_id = str(body.get("device_id") or "")
        if device_id in app.state.channel.online():
            try:
                # Best effort, and short. The browser a stop button is pressed
                # on is often the browser that has stopped answering, and a stop
                # that hangs for the full command deadline -- or raises out of
                # the route -- is a stop button that looks broken to the person
                # holding it. The flag above already stopped the run; this only
                # saves the extension a step it is mid-way through.
                await app.state.channel.send(
                    device_id,
                    kind="abort",
                    run_id=run_id,
                    payload={"run_id": run_id},
                    deadline_s=K_ABORT_DEADLINE_S,
                )
            except DeviceUnreachable:
                pass
        return {"aborted": True}

    @app.post("/v1/chat", dependencies=[Depends(authorised)])
    async def chat(body: dict[str, Any]) -> dict[str, Any]:
        """Offers. Never starts."""
        from rig.entry import understand
        from rig.workflows import known_workflows

        got = await understand(
            str(body.get("utterance") or ""),
            known_workflows(store, tenant),
            app.state.asker,
            settings().plan_model,
        )
        return {"workflow_id": got.workflow_id, "values": got.values, "missing": got.missing}

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return (Path(__file__).parent / "web" / "index.html").read_text()

    return app


# asyncio.create_task's return value is the only strong reference to a running
# task: the loop keeps a weak one, so a discarded task can be garbage-collected
# mid-execution and the reading simply never finishes. The documented fix is to
# hold it until it is done.
_reading_tasks: set[asyncio.Task[None]] = set()

# The same weak-reference problem, for runs.
_run_tasks: set[asyncio.Task[None]] = set()


async def _perform(work: Coroutine[Any, Any, object]) -> None:
    try:
        await work
    except Exception:
        # `run_workflow` re-raises anything but a browser that went away, after
        # saving the run as failed. The record is already right; what is left is
        # a task exception nobody retrieves, which asyncio reports at garbage
        # collection time from no particular place. Logged here instead, beside
        # the run it belongs to, and never allowed to take the server down.
        log.exception("a run stopped on an error; its record says failed")


def _spawn_run(work: Coroutine[Any, Any, object]) -> None:
    task = asyncio.create_task(_perform(work))
    _run_tasks.add(task)
    task.add_done_callback(_run_tasks.discard)


def _spawn_reading(store: Store, asker: Asker, tenant: str) -> asyncio.Task[None]:
    task = asyncio.create_task(_read_soon(store, asker, tenant))
    _reading_tasks.add(task)
    task.add_done_callback(_reading_tasks.discard)
    return task


async def _read_soon(store: Store, asker: Asker, tenant: str) -> None:
    try:
        # Drain, do not take one page. read_new_gestures reads at most 200 and
        # fires once per batch, while a single upload can carry 500 gestures --
        # so the remainder waited for another batch that may never come. When
        # capture stops for the day, those readings never happen at all.
        # Bounded because every pass must reduce the unread set: a pass that
        # returns 0 ends it, and the cap is a backstop against a row that
        # cannot be read and would otherwise spin.
        for _ in range(MAX_READING_PASSES):
            if not await read_new_gestures(store, asker, settings().intent_model, tenant):
                return
    except Exception:  # a reading loop must not take the process down with it
        # Still caught, so one bad row cannot end the process -- but never
        # silently. Nothing else in this system would notice: no intent rows
        # appear, /v1/spend keeps saying 0 read, and the page looks exactly
        # like an operator who has done nothing all morning. That is the
        # failure the extension names at service-worker.js:422, and the rig
        # was making the opposite choice at the other end of the same wire.
        log.exception("the reading loop stopped; gestures are left unread")


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
