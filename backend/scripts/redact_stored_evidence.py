from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys

import boto3
from botocore.config import Config
from sqlalchemy import select, update

from sro.application.observation.redact import redact_events
from sro.config import get_settings
from sro.infrastructure.db.models import ObservationBatchRow
from sro.infrastructure.db.session import create_engine, create_session_factory

LIVE = {
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."),
    "oauth code": re.compile(r"[?&]code=[A-Za-z0-9._~+/-]{16,}"),
    "bearer": re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{20,}"),
    "severed token": re.compile(r"\u00abredacted\u00bb[.\-_][A-Za-z0-9._~+/-]{16,}"),
    "long b64 run": re.compile(r"[A-Za-z0-9_-]{60,}"),
}

ADVISORY = {"long b64 run"}


def _count(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in LIVE.items()}


def _client(settings: object) -> object:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,  # type: ignore[attr-defined]
        aws_access_key_id=settings.s3_access_key,  # type: ignore[attr-defined]
        aws_secret_access_key=settings.s3_secret_key,  # type: ignore[attr-defined]
        region_name=settings.s3_region,  # type: ignore[attr-defined]
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 2},
            connect_timeout=10,
            read_timeout=60,
        ),
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="", help="one tenant; default is every one")
    parser.add_argument("--apply", action="store_true", help="write the rewritten objects back")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--backup",
        action="store_true",
        help="copy each object to <key>.pre-redaction before overwriting it",
    )
    args = parser.parse_args()

    settings = get_settings()
    store = _client(settings)
    bucket = settings.s3_bucket

    query = select(ObservationBatchRow)
    if args.tenant:
        query = query.where(ObservationBatchRow.tenant_id == args.tenant)
    query = query.order_by(ObservationBatchRow.started_at)

    engine = create_engine(settings.database_url)
    factory = create_session_factory(engine)
    async with factory() as session:
        rows = list((await session.execute(query)).scalars())

    print(f"{len(rows)} batch(es)" + (f" for {args.tenant}" if args.tenant else ""))
    print("DRY RUN -- nothing is written. Pass --apply to rewrite.\n" if not args.apply else "")

    before: dict[str, int] = dict.fromkeys(LIVE, 0)
    after: dict[str, int] = dict.fromkeys(LIVE, 0)
    changed = failed = backed = 0

    for index, row in enumerate(rows, start=1):
        if args.limit and index > args.limit:
            break
        key = row.uri.split(f"s3://{bucket}/", 1)[-1]
        try:
            raw = store.get_object(Bucket=bucket, Key=key)["Body"].read()  # type: ignore[attr-defined]
        except Exception as problem:
            print(f"  {row.id}: unreadable ({type(problem).__name__}) -- left alone")
            failed += 1
            continue

        text = raw.decode("utf8", "replace")
        was = _count(text)
        for name, n in was.items():
            before[name] += n

        try:
            events = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as problem:
            print(f"  {row.id}: unparseable ({problem}) -- left alone")
            failed += 1
            continue
        cleaned = redact_events(events)
        payload = (
            "\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in cleaned)
            + "\n"
        ).encode()
        now = _count(payload.decode("utf8", "replace"))
        for name, n in now.items():
            after[name] += n

        if payload == raw:
            continue

        changed += 1
        moved = {name: (was[name], now[name]) for name in LIVE if was[name] != now[name]}
        note = f"  {row.id}: {len(raw):,} -> {len(payload):,} bytes"
        if moved:
            note += "   " + ", ".join(f"{k} {a}->{b}" for k, (a, b) in moved.items())
        print(note)

        if not args.apply:
            continue

        if args.backup:
            spare = f"{key}.pre-redaction"
            try:
                store.head_object(Bucket=bucket, Key=spare)  # type: ignore[attr-defined]
            except Exception:
                store.copy_object(  # type: ignore[attr-defined]
                    Bucket=bucket, Key=spare, CopySource={"Bucket": bucket, "Key": key}
                )
                backed += 1

        store.put_object(  # type: ignore[attr-defined]
            Bucket=bucket, Key=key, Body=payload, ContentType="application/x-ndjson"
        )
        async with factory() as session:
            await session.execute(
                update(ObservationBatchRow)
                .where(ObservationBatchRow.id == row.id)
                .values(byte_count=len(payload))
            )
            await session.commit()

    await engine.dispose()

    print(f"\n{'rewrote' if args.apply else 'would rewrite'} {changed} object(s), {failed} failed")
    if args.apply and args.backup:
        print(f"  {backed} original(s) kept beside their key as <key>.pre-redaction")
    elif args.apply:
        print("  NO BACKUP was taken -- the originals are gone. --backup keeps them.")
    print("  what a reader greps for, before -> after:")
    for name in LIVE:
        if name in ADVISORY:
            mark = "   (advisory)"
        else:
            mark = "" if after[name] == 0 else "   STILL PRESENT"
        print(f"    {name:14s} {before[name]:4d} -> {after[name]:4d}{mark}")
    if any(after[name] for name in LIVE if name not in ADVISORY):
        print("\n  NOT CLEAN. Do not describe this store as redacted.")
    if not args.apply and changed:
        print("\n  nothing was written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
