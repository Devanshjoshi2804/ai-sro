"""Replay captured batches into the rig.

The extension mirrors an upload to the rig only while the rig's URL and token
are set in its options, so everything captured before that went to the backend
alone. This posts the backend's own stored batches to the rig's /v1/observations
so the rig starts from the evidence that already exists rather than from zero.

Reads only. It never writes to the backend, and the rig refuses a batch id it
already holds, so running it twice costs two rejected requests and nothing else.

    uv run python scripts/mirror_backfill.py --rig http://127.0.0.1:8100 \
        --token "$RIG_TOKEN" --tenant acme [--since 2026-09-01] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sqlalchemy import select

from sro.config import get_settings
from sro.infrastructure.blob.minio_store import MinioBlobStore
from sro.infrastructure.db.models import ObservationBatchRow, ObservationPolicyRow
from sro.infrastructure.db.session import create_engine, create_session_factory


def _post(url: str, token: str, body: dict) -> tuple[int, str]:
    request = urllib.request.Request(  # noqa: S310 -- http(s), from a flag
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 -- http(s) only, from a flag
            return response.status, response.read()[:200].decode("utf8", "replace")
    except urllib.error.HTTPError as problem:
        return problem.code, problem.read()[:200].decode("utf8", "replace")
    except Exception as problem:
        return 0, f"{type(problem).__name__}: {problem}"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig", default="http://127.0.0.1:8100")
    parser.add_argument("--token", required=True, help="the rig's ingest token")
    parser.add_argument("--tenant", default="acme")
    parser.add_argument("--since", default="", help="ISO date; default is everything")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many batches")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-policy", action="store_true", help="replay everything, ignoring the exclusions"
    )
    args = parser.parse_args()

    settings = get_settings()

    # The batches were captured under whatever policy was in force then, and
    # replaying them into a rig governed by today's policy would ingest exactly
    # what the tenant has since decided not to watch. The policy is the one
    # source of truth for that, so it is read rather than restated here.
    excluded: tuple[str, ...] = ()
    if not args.no_policy:
        async with create_session_factory(create_engine(settings.database_url))() as probe:
            found = (
                (
                    await probe.execute(
                        select(ObservationPolicyRow).where(
                            ObservationPolicyRow.tenant_id == args.tenant
                        )
                    )
                )
                .scalars()
                .first()
            )
        excluded = tuple((found.policy or {}).get("exclude_hosts", ())) if found else ()
        print(f"excluding {len(excluded)} host(s) the tenant no longer watches")

    def watched(event: dict) -> bool:
        url = (
            event.get("gesture", {}).get("url")
            or event.get("request", {}).get("url")
            or event.get("url")
            or ""
        )
        host = urlsplit(url).hostname or ""
        if not host:
            # No host is not the same as a host nobody excluded: a page event
            # with no url is kept, because dropping evidence for being
            # unattributable is the failure this whole rig is built against.
            return True
        return not any(host == bad or host.endswith(f".{bad}") for bad in excluded)

    blobs = MinioBlobStore(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
    )

    query = select(ObservationBatchRow).where(ObservationBatchRow.tenant_id == args.tenant)
    if args.since:
        query = query.where(
            ObservationBatchRow.started_at >= datetime.fromisoformat(args.since).replace(tzinfo=UTC)
        )
    query = query.order_by(ObservationBatchRow.started_at)

    engine = create_engine(settings.database_url)
    async with create_session_factory(engine)() as session:
        rows = list((await session.execute(query)).scalars())

    print(f"{len(rows)} batch(es) for {args.tenant}")
    if not rows:
        print("  nothing to replay -- check the tenant name against the backend's own")
        return 0

    sent = events = failed = 0
    for index, row in enumerate(rows, start=1):
        if args.limit and index > args.limit:
            break
        # `uri` is s3://bucket/key and the port takes the key alone.
        key = row.uri.split(f"s3://{settings.s3_bucket}/", 1)[-1]
        try:
            raw = await blobs.get(key)
        except Exception as problem:
            print(f"  {row.id}: blob unreadable ({type(problem).__name__}) -- skipped")
            failed += 1
            continue

        # The blob is ndjson -- one event per line, as the extension streamed
        # it -- not an object with an `events` array.
        parsed = [
            json.loads(line) for line in raw.decode("utf8", "replace").splitlines() if line.strip()
        ]
        # The rig re-declares the wire protocol rather than importing it, so the
        # batch goes over as the extension sent it. Anything the rig's own
        # parser refuses it names in the response; it does not reject the batch.
        body = {
            "batch_id": row.id,
            "device_id": row.device_id,
            "started_at": row.started_at.isoformat(),
            "ended_at": row.ended_at.isoformat(),
            "mode": row.mode,
            "recording_id": row.recording_id,
            "events": parsed,
        }
        kept = [event for event in parsed if watched(event)]
        dropped = len(parsed) - len(kept)
        body["events"] = kept
        count = len(kept)
        if not count:
            print(f"  {row.id}: all {dropped} event(s) on excluded hosts -- skipped")
            continue
        if args.dry_run:
            print(f"  would send {row.id}  {count} event(s)  {row.started_at.isoformat()}")
            events += count
            continue

        status, detail = _post(f"{args.rig}/v1/observations", args.token, body)
        if status == 202:
            sent += 1
            events += count
            print(f"  {row.id}: {count} accepted, {dropped} on excluded hosts")
        else:
            failed += 1
            print(f"  {row.id}: {status} {detail}")

    await engine.dispose()
    verb = "would replay" if args.dry_run else "replayed"
    print(f"\n{verb} {sent} batch(es), {events} event(s), {failed} failed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
