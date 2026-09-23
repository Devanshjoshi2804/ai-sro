from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping
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
    ours = settings.our_own_hosts()
    print(f"excluding {len(ours)} host(s) that are this system recording itself")

    def watched(event: dict) -> bool:
        def _at(key: str) -> object:
            nested = event.get(key)
            return nested.get("url") if isinstance(nested, Mapping) else None

        url = _at("gesture") or _at("request") or event.get("url") or ""
        if not isinstance(url, str):
            url = ""
        if (urlsplit(url).netloc or "").lower() in ours:
            return False
        host = urlsplit(url).hostname or ""
        if not host:
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
        key = row.uri.split(f"s3://{settings.s3_bucket}/", 1)[-1]
        try:
            raw = await blobs.get(key)
        except Exception as problem:
            print(f"  {row.id}: blob unreadable ({type(problem).__name__}) -- skipped")
            failed += 1
            continue

        parsed = [
            json.loads(line) for line in raw.decode("utf8", "replace").splitlines() if line.strip()
        ]
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
