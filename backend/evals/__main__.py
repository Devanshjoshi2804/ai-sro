from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from evals.run import run_ci, run_suite, write_candidates


def _at_least_one(text: str) -> int:
    if int(text) < 1:
        raise argparse.ArgumentTypeError("a limit is at least 1")
    return int(text)


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="evals")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run")
    one.add_argument("--suite", required=True)
    one.add_argument("--tenant", required=True)
    one.add_argument("--baseline", action="store_true")
    one.add_argument("--limit", type=_at_least_one)
    one.add_argument("--rebuild", action="store_true")
    one.add_argument(
        "--repeat",
        type=_at_least_one,
        default=1,
        help="run every case N times; it counts only if all N pass (pass^k)",
    )
    ci = sub.add_parser("ci")
    ci.add_argument("--live", action="store_true")
    red = sub.add_parser("redact")
    red.add_argument("--suite", required=True)
    red.add_argument("--tenant", required=True)
    args = parser.parse_args(argv)
    if args.command == "run" and args.baseline and args.limit:
        parser.error("a baseline is the whole case set: --limit and --baseline do not mix")
    return args


def main() -> int:
    args = arguments()
    if args.command == "run":
        return asyncio.run(
            run_suite(
                args.suite,
                args.tenant,
                baseline=args.baseline,
                limit=args.limit,
                rebuild=args.rebuild,
                repeat=args.repeat,
            )
        )
    if args.command == "ci":
        return asyncio.run(run_ci(live=args.live))
    return asyncio.run(write_candidates(args.suite, args.tenant))


if __name__ == "__main__":
    raise SystemExit(main())
