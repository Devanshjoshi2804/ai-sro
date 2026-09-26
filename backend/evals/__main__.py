from __future__ import annotations

import argparse
import asyncio

from evals.run import run_ci, run_suite, write_candidates


def main() -> int:
    parser = argparse.ArgumentParser(prog="evals")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run")
    one.add_argument("--suite", required=True)
    one.add_argument("--tenant", required=True)
    one.add_argument("--baseline", action="store_true")
    one.add_argument("--limit", type=int)
    ci = sub.add_parser("ci")
    ci.add_argument("--live", action="store_true")
    red = sub.add_parser("redact")
    red.add_argument("--suite", required=True)
    red.add_argument("--tenant", required=True)
    args = parser.parse_args()
    if args.command == "run":
        return asyncio.run(
            run_suite(args.suite, args.tenant, baseline=args.baseline, limit=args.limit)
        )
    if args.command == "ci":
        return asyncio.run(run_ci(live=args.live))
    return asyncio.run(write_candidates(args.suite, args.tenant))


raise SystemExit(main())
