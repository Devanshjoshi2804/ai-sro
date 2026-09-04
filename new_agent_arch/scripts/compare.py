"""Two pipelines, one day of evidence, side by side.

The production pipeline partitions candidates by host, so a job spanning two
systems is structurally two candidates that never join. The rig runs one model
pass over a window and can, in principle, see it whole. This puts the two
answers next to each other on the same traffic so the claim can be checked
rather than argued.

It reads both services over HTTP and changes nothing in either. Mining is the
one call that costs money, and it only happens with --mine.

    uv run python scripts/compare.py --tenant acme
    uv run python scripts/compare.py --tenant acme --mine

Backend token: `make token tenant=acme principal=you` at the repo root.
Rig token: RIG_INGEST_TOKEN in new_agent_arch/.env.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from collections import Counter
from typing import Any
from urllib.parse import urlparse


def _env_file(path: pathlib.Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def _get(url: str, token: str) -> Any:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as problem:
        return {
            "_error": f"HTTP {problem.code}",
            "_body": problem.read()[:200].decode("utf8", "replace"),
        }
    except Exception as problem:  # noqa: BLE001 -- a comparison script reports, it does not raise
        return {"_error": f"{type(problem).__name__}: {problem}"}


def _post(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url, data=b"", method="POST", headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as problem:
        return {
            "_error": f"HTTP {problem.code}",
            "_body": problem.read()[:200].decode("utf8", "replace"),
        }
    except Exception as problem:  # noqa: BLE001
        return {"_error": f"{type(problem).__name__}: {problem}"}


def _host(url: str | None) -> str:
    return urlparse(url).netloc if url else ""


def main() -> int:
    here = pathlib.Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default="acme")
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--rig", default="http://127.0.0.1:8100")
    parser.add_argument("--backend-token", default=os.environ.get("SRO_TOKEN", ""))
    parser.add_argument("--rig-token", default=_env_file(here / ".env", "RIG_INGEST_TOKEN"))
    parser.add_argument("--mine", action="store_true", help="run a mining pass first (billed)")
    args = parser.parse_args()

    if not args.rig_token:
        print("no rig token: set RIG_INGEST_TOKEN in new_agent_arch/.env or pass --rig-token")
        return 2

    print(f"=== what the rig has seen ({args.tenant}) ===")
    streams = _get(f"{args.rig}/v1/streams", args.rig_token)
    if "_error" in streams:
        print(f"  rig unreachable: {streams['_error']}  -- is `make serve` running on :8100?")
        return 2
    total = 0
    for row in streams.get("streams", []):
        total += row.get("gestures", 0)
        print(f"  {row.get('stream_id')}: {row.get('gestures')} gestures")
    if not total:
        print("  nothing yet. The extension mirrors uploads only while its rig URL and")
        print("  token are set in the options page, and only for hosts the tenant grants.")

    spend = _get(f"{args.rig}/v1/spend?since=1970-01-01T00:00:00Z", args.rig_token)
    if "_error" not in spend:
        print(
            f"  read {spend.get('gestures_read')}/{spend.get('gestures')}"
            f"  ${spend.get('cost_usd', 0):.4f} reading"
            f"  ${spend.get('mining_usd', 0):.4f} mining over {spend.get('passes')} pass(es)"
            f"  thinking {spend.get('thought_tokens')} tok"
        )
        if spend.get("unpriced") or spend.get("mining_unpriced"):
            print(
                f"  UNPRICED: {spend.get('unpriced')} reading(s),"
                f" {spend.get('mining_unpriced')} pass(es) -- those dollars are not the bill"
            )

    if args.mine:
        print("\n=== mining (billed) ===")
        result = _post(f"{args.rig}/v1/mine", args.rig_token)
        if "_error" in result:
            print(f"  refused: {result['_error']} {result.get('_body', '')}")
        else:
            print(
                f"  proposed {result.get('proposed')}  kept {result.get('kept')}"
                f"  rejected {len(result.get('rejections', []))}"
                f"  coverage {result.get('coverage', {}).get('coverage')}"
                f"  lopsided {result.get('lopsided')}"
            )
            for rejection in result.get("rejections", []):
                print(f"    refused {rejection.get('workflow_title')!r}: {rejection.get('reason')}")
            if result.get("error"):
                print(f"    the model refused this pass: {result['error']}")

    print("\n=== the rig's workflows ===")
    flows = _get(f"{args.rig}/v1/workflows", args.rig_token)
    rig_rows = flows.get("workflows", []) if "_error" not in flows else []
    if "_error" in flows:
        print(f"  {flows['_error']}")
    cross = 0
    for flow in rig_rows:
        systems = flow.get("systems") or []
        mark = "  <-- CROSS-SYSTEM" if len({s for s in systems if s}) > 1 else ""
        cross += 1 if mark else 0
        print(f"  {flow.get('title')!r}  steps {len(flow.get('steps', []))}  {systems}{mark}")
    if not rig_rows:
        print("  none yet -- run with --mine once the rig has evidence")

    print(f"\n=== the production pipeline's candidates ({args.tenant}) ===")
    if not args.backend_token:
        print("  no backend token. `make token tenant=acme principal=you`, then")
        print("  export SRO_TOKEN=... or pass --backend-token")
        backend_rows: list[dict[str, Any]] = []
    else:
        candidates = _get(f"{args.backend}/v1/candidates?seen_at_least=1", args.backend_token)
        # The backend answers with a bare list; the rig answers with an object.
        # `"_error" in x` is true-ish on both a dict key and a list member, so
        # the type has to be checked before anything is read off it.
        if isinstance(candidates, dict) and "_error" in candidates:
            print(f"  {candidates['_error']} {candidates.get('_body', '')}")
            backend_rows = []
        else:
            backend_rows = (
                candidates if isinstance(candidates, list) else candidates.get("candidates", [])
            )
            by_host: Counter[str] = Counter()
            for row in backend_rows:
                host = row.get("host") or _host(row.get("url"))
                by_host[host] += 1
                print(f"  {row.get('title') or row.get('label') or row.get('id')!r}  host {host}")
            if by_host:
                print(f"  {len(backend_rows)} candidates across {len(by_host)} host(s)")

    print("\n=== the comparison ===")
    print(f"  rig workflows          {len(rig_rows)}, of which cross-system {cross}")
    print(f"  backend candidates     {len(backend_rows)}")
    if cross:
        print("  The rig produced a workflow spanning more than one host. The production")
        print("  pipeline partitions by host, so the same job is at best two candidates")
        print("  there, and nothing joins them.")
    elif rig_rows:
        print("  No cross-system workflow this pass. That is the expected answer while the")
        print("  captured evidence is single-host: see docs/new-agent-doc-arc/findings.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
