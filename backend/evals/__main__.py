from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence

from evals.feedback import run_feedback
from evals.run import run_ci, run_suite, write_candidates
from sro.domain.chat.feedback import DISMISSED, KINDS, NEW, REVIEWED, STATUSES


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
    fb = sub.add_parser(
        "feedback", help="review what went wrong in chat turns (see evals/feedback.py)"
    )
    fb.add_argument("--tenant", required=True)
    act = fb.add_subparsers(dest="action", required=True)
    ls = act.add_parser("list")
    ls.add_argument("--status", choices=STATUSES, default=NEW)
    ls.add_argument("--kind", choices=KINDS, default="")
    ls.add_argument("--limit", type=_at_least_one, default=20)
    act.add_parser("show").add_argument("id")
    mark = act.add_parser("mark")
    mark.add_argument("id")
    mark.add_argument("status", choices=(REVIEWED, DISMISSED))
    mark.add_argument("--note", default="")
    promote = act.add_parser("promote")
    promote.add_argument("id")
    promote.add_argument(
        "--expect", required=True, help='the right tools, e.g. "find_jobs,start_job"'
    )
    promote.add_argument("--args-json", default="{}", help="the last tool's exact arguments")
    suggest = act.add_parser("suggest", help="write a proposal per group of repeated problems")
    suggest.add_argument("--since", default="14d", help="how far back to look: 14d or 36h")
    suggest.add_argument("--min", type=_at_least_one, default=3, help="rows a group needs")
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
    if args.command == "feedback":
        return asyncio.run(run_feedback(args))
    return asyncio.run(write_candidates(args.suite, args.tenant))


if __name__ == "__main__":
    raise SystemExit(main())
