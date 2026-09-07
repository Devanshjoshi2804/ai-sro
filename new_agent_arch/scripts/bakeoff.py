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

from rig.bakeoff import DOORS, K_BURST, K_READ_GESTURES, Reading, Row, save, save_readings, sweep
from rig.claude import AnthropicAsker
from rig.models import PRICES, Asker, GeminiAsker, is_priced
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


def reachable(gemini: str, anthropic: str, wanted: tuple[str, ...]) -> bool:
    """Ask each vendor what it will serve this key, and say whether every model
    named is on that list.

    Listing is free and it is the only honest way to find out. A model name the
    API does not have comes back as a 404 on the first real call, halfway
    through a sweep, having already billed for whatever ran before it -- and
    `config.mine_model` was exactly that for weeks: "gemini-3.1-pro", which
    models.list() does not offer.
    """
    offered: dict[str, set[str]] = {"gemini": set(), "anthropic": set()}
    problems: list[str] = []

    if gemini:
        try:
            from google import genai

            # Held in a local, not built inline: the SDK closes the underlying
            # http client when the Client is collected, and a temporary is
            # collected between `models.list()` returning its pager and the
            # loop iterating it -- which reads as "the client has been closed"
            # and looks exactly like a network failure.
            client = genai.Client(api_key=gemini)
            for entry in client.models.list():
                name = str(getattr(entry, "name", "") or "")
                offered["gemini"].add(name.removeprefix("models/"))
            print(f"gemini:    key valid, {len(offered['gemini'])} models offered")
        except Exception as problem:  # noqa: BLE001 -- the point is to report it
            problems.append(f"gemini: {type(problem).__name__}: {problem}")
            print(f"gemini:    UNREACHABLE -- {type(problem).__name__}: {problem}")

    if anthropic:
        try:
            import anthropic as sdk

            vendor = sdk.Anthropic(api_key=anthropic)
            listing = vendor.models.list(limit=100)
            for entry in listing.data:
                offered["anthropic"].add(str(getattr(entry, "id", "")))
            print(f"anthropic: key valid, {len(offered['anthropic'])} models offered")
        except Exception as problem:  # noqa: BLE001 -- the point is to report it
            problems.append(f"anthropic: {type(problem).__name__}: {problem}")
            print(f"anthropic: UNREACHABLE -- {type(problem).__name__}: {problem}")

    print()
    every = True
    for model in wanted:
        vendor = "anthropic" if model.startswith("claude") else "gemini"
        if not offered[vendor]:
            print(f"  ?  {model:<30} {vendor} could not be asked")
            every = False
            continue
        if model in offered[vendor]:
            print(
                f"  ok {model:<30} served, and priced at {PRICES[model]} per Mtok"
                if model in PRICES
                else f"  ok {model:<30} served, but NOT in PRICES"
            )
        else:
            near = sorted(n for n in offered[vendor] if n.split("-")[0] in model)[:4]
            print(f"  NO {model:<30} not offered. nearest: {', '.join(near) or '(none)'}")
            every = False
    return every


def _agreement(readings: list[Reading]) -> dict[str, tuple[int, int]]:
    """For every pair of models, how often they gave the same act to the same
    gesture. The one number that says whether a cheaper model is reading the
    same day or a different one."""
    by_model: dict[str, dict[str, str | None]] = {}
    for reading in readings:
        by_model.setdefault(reading.model, {})[reading.gesture_id] = reading.act
    names = sorted(by_model)
    out: dict[str, tuple[int, int]] = {}
    for i, one in enumerate(names):
        for two in names[i + 1 :]:
            shared = set(by_model[one]) & set(by_model[two])
            same = sum(1 for g in shared if by_model[one][g] == by_model[two][g])
            out[f"{one} vs {two}"] = (same, len(shared))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="rig.db", help="the store to compare on; never written")
    parser.add_argument("--out", default="bakeoff-out", help="where the per-model copies go")
    parser.add_argument("--tenant", default="new")
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--doors", default=",".join(DOORS))
    parser.add_argument(
        "--gestures",
        type=int,
        default=K_READ_GESTURES,
        help="gestures the read door reads; 0 is the whole day, which is the point",
    )
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
    parser.add_argument(
        "--check",
        action="store_true",
        help="ask each vendor which models it will actually serve this key, then stop",
    )
    parser.add_argument(
        "--effort",
        choices=("minimal", "low", "medium", "high"),
        help="reasoning effort for the mining pass; the rig ships 'high'."
        " A model whose thinking is billed inside its output ceiling can think"
        " itself out of room to answer, and this is the knob that gives it room.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="empty each copy of what an earlier pass found, so the mine door measures something",
    )
    parser.add_argument("--dry", action="store_true", help="print the plan, ask nothing")
    args = parser.parse_args()

    source = Path(args.db)
    if not source.exists():
        raise SystemExit(f"no store at {source}")

    if args.effort:
        # An instrument reaching into the module it measures. The mining pass
        # reads this constant at call time, and the alternative -- threading an
        # effort through mine() and propose() -- would change the rig to
        # measure it.
        import rig.umbrella

        rig.umbrella.K_EFFORT = args.effort  # type: ignore[assignment]
        print(f"effort:   {args.effort} for the mining pass (the rig ships 'high')")

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

    if args.check:
        every = reachable(gemini, anthropic, wanted)
        print(
            "\nevery model named is reachable and priced"
            if every
            else "\nsome model is not reachable; fix the name or the key before spending"
        )
        raise SystemExit(0 if every else 1)

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

    def keep(some: list[Row], found: list[Reading]) -> None:
        """Each door's findings, the moment it is done. A sweep is a long run
        of paid calls, and anything that fails at the end of one must not throw
        away what the earlier doors already bought."""
        save(store, some)
        save_readings(store, found)
        for row in some:
            print(f"  saved {row.model} {row.door}: ${row.cost_usd:.4f}", flush=True)

    rows: list[Row]
    readings: list[Reading]
    rows, readings = asyncio.run(
        sweep(
            source=source,
            out=Path(args.out),
            models=tuple(models),
            asker_for=asker_for,
            tenant=args.tenant,
            gestures=args.gestures,
            bursts=args.burst,
            twice=not args.once,
            fresh=args.fresh,
            budget_usd=args.budget_usd,
            doors=doors,
            sink=keep,
        )
    )

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
    agree = _agreement(readings)
    if agree:
        print("\nagreement on the same gesture, model against model:")
        for pair, (same, seen) in sorted(agree.items()):
            print(f"  {pair:<58} {same}/{seen} = {same / seen:.0%}" if seen else f"  {pair} none")
    print(
        f"\nsweep total ${sum(r.cost_usd for r in rows):.4f};"
        f" {len(readings)} readings kept; the page draws it under `models`"
    )


if __name__ == "__main__":
    sys.exit(main())
