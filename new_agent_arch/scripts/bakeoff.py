"""Run one day of real evidence past several models and write down what each did.

Not part of the build and not imported by anything: an instrument, like
`measure.py`, which is its single-model ancestor. Every model gets its own copy
of the store, so they start from byte-identical evidence and cannot see each
other's writings. The results land in the store the API serves, and the rig's
page draws them under `models`.

    RIG_GEMINI_API_KEY=... ANTHROPIC_API_KEY=... \
        uv run python scripts/bakeoff.py --db rig.db --tenant new

Keys are read from the environment, then from `new_agent_arch/.env`, then from
`backend/.env`, under any of the names either project uses. Gemini models are
asked through `GeminiAsker`, `claude-*` through `AnthropicAsker`; a model whose
vendor has no key is skipped by name rather than failing the sweep.

Money is real, and this spends it twice per model. `--budget-usd` is the
ceiling for the whole sweep and a door that would start over it is skipped with
its reason in the row. `--dry` asks nothing and prints the plan.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Before any rig import: settings are read once and cached, and the rig's own
# daily cap would stop a deliberate measurement halfway through. The sweep's
# own --budget-usd is the ceiling that applies here.
os.environ.setdefault("RIG_DAILY_USD_CAP", "-1")

from rig.bakeoff import DOORS, K_BURST, K_READ_GESTURES, Row, save, sweep
from rig.claude import AnthropicAsker
from rig.models import Asker, GeminiAsker, is_priced
from rig.store import Store

MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.1-pro-preview",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-5",
)

GEMINI_KEYS = ("RIG_GEMINI_API_KEY", "GEMINI_API_KEY", "SRO_GEMINI_API_KEY")
ANTHROPIC_KEYS = ("RIG_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", "SRO_ANTHROPIC_API_KEY")


def _env_files() -> dict[str, str]:
    """Both projects' .env files, parsed once. The operator keeps one key in
    the rig's and may put the other in the backend's; neither location is wrong
    and hunting for it by hand is how a sweep runs with four models."""
    found: dict[str, str] = {}
    here = Path(__file__).resolve().parent.parent
    for path in (here / ".env", here.parent / "backend" / ".env"):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            found.setdefault(name.strip(), value.strip().strip("'\""))
    return found


def key_for(names: tuple[str, ...], env: dict[str, str]) -> str:
    for name in names:
        value = os.environ.get(name) or env.get(name, "")
        if value:
            return value
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="rig.db", help="the store to compare on; never written")
    parser.add_argument("--out", default="bakeoff-out", help="where the per-model copies go")
    parser.add_argument("--tenant", default="new")
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--doors", default=",".join(DOORS))
    parser.add_argument("--gestures", type=int, default=K_READ_GESTURES)
    parser.add_argument("--burst", type=int, default=K_BURST, help="calls fired at once")
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=5.0,
        help="ceiling for the whole sweep; negative means no ceiling",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="read the day once; without it the mine door reads it twice and reports stability",
    )
    parser.add_argument("--dry", action="store_true", help="print the plan, ask nothing")
    args = parser.parse_args()

    source = Path(args.db)
    if not source.exists():
        raise SystemExit(f"no store at {source}")

    env = _env_files()
    gemini, anthropic = key_for(GEMINI_KEYS, env), key_for(ANTHROPIC_KEYS, env)
    wanted = tuple(m.strip() for m in args.models.split(",") if m.strip())
    doors = tuple(d.strip() for d in args.doors.split(",") if d.strip())

    models: list[str] = []
    for model in wanted:
        vendor_key = anthropic if model.startswith("claude") else gemini
        if not vendor_key:
            print(f"  skipping {model}: no key for its vendor")
            continue
        if not is_priced(model):
            # A model missing from PRICES bills at 0.0 with unpriced=True, and
            # a comparison whose whole point is cost must not carry a row that
            # silently reads free.
            print(f"  skipping {model}: not in PRICES, so its bill would read $0.00")
            continue
        models.append(model)
    if not models:
        raise SystemExit("no model has both a key and a price")

    def asker_for(model: str) -> Asker:
        return AnthropicAsker(anthropic) if model.startswith("claude") else GeminiAsker(gemini)

    store = Store(source)
    read = store.query("SELECT count(*) AS n FROM gestures WHERE tenant = ?", (args.tenant,))
    print(f"evidence: {read[0]['n']} gestures for tenant {args.tenant}")
    print(f"models:   {', '.join(models)}")
    print(
        f"doors:    {', '.join(doors)} (read reads {args.gestures} gestures,"
        f" burst fires {args.burst} at once,"
        f" mine reads the day {'once' if args.once else 'twice, for stability'})"
    )
    print(
        "budget:   no ceiling"
        if args.budget_usd < 0
        else f"budget:   ${args.budget_usd:.2f} for the sweep"
    )
    if args.dry:
        print("\n--dry: nothing was asked and nothing was spent")
        return

    rows: list[Row] = asyncio.run(
        sweep(
            source=source,
            out=Path(args.out),
            models=tuple(models),
            asker_for=asker_for,
            tenant=args.tenant,
            gestures=args.gestures,
            bursts=args.burst,
            twice=not args.once,
            budget_usd=args.budget_usd,
            doors=doors,
        )
    )
    save(store, rows)

    print(f"\n{'model':<28} {'door':<5} {'calls':>5} {'p50ms':>8} {'cost':>9}  outcome")
    for row in sorted(rows, key=lambda r: (r.door, r.cost_usd)):
        if row.error:
            outcome = row.error
        elif row.door == "read":
            outcome = f"{row.usable}/{row.gestures} usable"
        elif row.door == "burst":
            outcome = f"{row.speedup}x of {row.calls} at once in {row.seconds}s"
        else:
            outcome = f"kept {row.kept} of {row.proposed}, cross-system {row.cross_system}"
        print(
            f"{row.model:<28} {row.door:<5} {row.calls:>5} {row.p50_ms:>8.0f}"
            f" {row.cost_usd:>9.4f}  {outcome}"
        )
    print(f"\nsweep total ${sum(r.cost_usd for r in rows):.4f}; the page draws it under `models`")


if __name__ == "__main__":
    sys.exit(main())
