from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import asyncpg
import httpx


def _database_url() -> str:
    url = os.environ.get("SRO_DATABASE_URL")
    if not url:
        with Path(".env").open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("SRO_DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
    if not url:
        raise SystemExit("no SRO_DATABASE_URL in the environment or .env")
    return url.replace("+asyncpg", "").replace("+psycopg", "")


async def _snapshot(conn: asyncpg.Connection) -> dict[str, Any]:
    passes = await conn.fetch(
        "select id, proposed, kept, learned_parameters, cost_usd, coverage,"
        " lopsided, error from mining_passes order by started_at"
    )
    workflows = await conn.fetch(
        "select id, title, jsonb_array_length(coalesce(parameters,'[]'::jsonb)) n"
        " from workflows order by id"
    )
    return {
        "passes": [dict(row) for row in passes],
        "workflows": {row["title"]: row["n"] for row in workflows},
        "gestures": await conn.fetchval("select count(*) from gestures"),
        "total_parameters": sum(row["n"] for row in workflows),
    }


async def main() -> int:
    tenant = os.environ.get("PROBE_TENANT", "acme")

    from sro.interface.http.app import app

    conn = await asyncpg.connect(_database_url())
    before = await _snapshot(conn)

    print(
        f"BEFORE  gestures={before['gestures']}  passes={len(before['passes'])}"
        f"  workflows={len(before['workflows'])}"
        f"  parameters={before['total_parameters']}"
    )
    for title, n in before["workflows"].items():
        print(f"          {n}  {title}")

    minted = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "sro.cli.mint",
        tenant,
        "operator",
        "--days",
        "1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await minted.communicate()
    if minted.returncode != 0:
        print(f"could not mint a token: {err.decode().strip()}")
        await conn.close()
        return 1
    token = out.decode().strip()

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://probe") as client,
    ):
        print("\nPOST /v1/mine ...")
        response = await client.post(
            "/v1/mine", headers={"Authorization": f"Bearer {token}"}, timeout=900.0
        )
        print(f"  status {response.status_code}")
        try:
            body = response.json()
        except ValueError:
            print(f"  body was not JSON: {response.text[:400]}")
            await conn.close()
            return 1
        print(json.dumps(body, indent=2)[:3000])

    after = await _snapshot(conn)
    await conn.close()

    print(
        f"\nAFTER   passes={len(after['passes'])}"
        f"  workflows={len(after['workflows'])}"
        f"  parameters={after['total_parameters']}"
    )
    for title, n in after["workflows"].items():
        was = before["workflows"].get(title)
        mark = "  (new)" if was is None else ("  (WIDENED)" if n > was else "")
        print(f"          {n}  {title}{mark}")

    new_passes = [p for p in after["passes"] if p["id"] not in {q["id"] for q in before["passes"]}]

    print("\n--- the questions this probe exists to answer ---")
    print(f"1. route answered 2xx ...................... {response.status_code < 300}")
    print(f"2. a mining_passes row was written ......... {len(new_passes) == 1}")
    if new_passes:
        row = new_passes[0]
        print(
            f"     proposed={row['proposed']} kept={row['kept']}"
            f" learned_parameters={row['learned_parameters']}"
            f" cost=${row['cost_usd']:.4f} error={row['error']!r}"
        )
        print(
            f"3. learned_parameters survived the pass .... {row['learned_parameters'] > 0}"
            "   <- FIRST TIME if True"
        )
        print(
            f"4. body's learned_parameters matches row ... "
            f"{body.get('learned_parameters') == row['learned_parameters']}"
        )
        print(
            f"5. body's cost matches the row ............. "
            f"{abs(float(body.get('cost_usd', -1)) - float(row['cost_usd'])) < 1e-9}"
        )
    widened = {
        t: (before["workflows"].get(t), n)
        for t, n in after["workflows"].items()
        if before["workflows"].get(t) is not None and n > before["workflows"][t]
    }
    print(f"6. any workflow's parameters widened ....... {bool(widened)}  {widened or ''}")
    print(
        f"\nACCEPTANCE (spec asks 8 of 8 workflows, 10 of 11 values): "
        f"{len(after['workflows'])} of 8 workflows, {after['total_parameters']} of 11 values"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
