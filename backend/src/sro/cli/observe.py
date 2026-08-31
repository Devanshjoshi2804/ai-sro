"""Switch passive observation on or off for one tenant. Shell access only.

Not an endpoint, and the reason is the same one that keeps ``mint`` here: there
is no role model, so every credential for a tenant can do everything that tenant
can do. A route that enabled observation would let any operator consent on their
colleagues' behalf, and ADR 008 makes this a contract conversation.

    python -m sro.cli.observe acme --on --exclude payroll.acme.com --keep-days 30
    python -m sro.cli.observe acme --off
    python -m sro.cli.observe acme            # just read it back
"""

from __future__ import annotations

import argparse
import asyncio
import json

from sro.application.context import RequestContext
from sro.container import build_container
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import PrincipalId, TenantId


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read or change a tenant's observation policy.")
    parser.add_argument("tenant")
    switch = parser.add_mutually_exclusive_group()
    switch.add_argument("--on", action="store_true", help="observation may happen")
    switch.add_argument("--off", action="store_true", help="observation stops")
    parser.add_argument(
        "--exclude",
        nargs="*",
        help="hosts never observed, replacing the current list. Finance, health "
        "and HR are named differently at every customer and belong here.",
    )
    parser.add_argument("--only", nargs="*", help="observe these hosts and nothing else")
    parser.add_argument("--keep-days", type=int, help="retention window for the evidence")
    trees = parser.add_mutually_exclusive_group()
    trees.add_argument(
        "--snapshots",
        action="store_true",
        help="read each page's accessibility structure while watching, not only while "
        "teaching. It is what makes a locator survive a re-render. Chrome shows a "
        "debugging banner on every watched tab for as long as this is on, unless the "
        "extension was force-installed by enterprise policy -- so turn it on for a fleet "
        "you manage, and leave it off for browsers you do not.",
    )
    trees.add_argument(
        "--no-snapshots", action="store_true", help="stop reading page structure while watching"
    )
    args = parser.parse_args(argv)

    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    container = build_container()
    ctx = RequestContext(
        tenant_id=TenantId(args.tenant),
        # The shell is the authority here; the name is for the record, not a check.
        principal_id=PrincipalId("shell"),
    )

    policy = await container.read_observation_policy().execute(ctx)
    changed = _apply(policy, args)
    if changed is not policy:
        await container.set_observation_policy().execute(ctx, policy=changed)

    print(
        json.dumps(
            {
                "tenant": args.tenant,
                "version": changed.version,
                "capture_enabled": changed.capture_enabled,
                "exclude_hosts": list(changed.exclude_hosts),
                "include_hosts": list(changed.include_hosts),
                "capture_snapshots": changed.capture_snapshots,
                "retention_days": changed.retention_days,
            },
            indent=2,
        )
    )
    if changed.capture_enabled and not changed.include_hosts:
        # Said every time, because the deny-list is the shape that fails
        # quietly: it protects the hosts somebody thought of, and a browser has
        # every host in it. Naming the systems is a minute's work and it is the
        # difference between observing a warehouse and observing a person.
        print(
            "\nnote: every site in the browser is observed except the excluded ones.\n"
            "      Name the systems instead:\n"
            f"      python -m sro.cli.observe {args.tenant} --only wms.example.com erp.example.com",
        )
    return 0


def _apply(policy: ObservationPolicy, args: argparse.Namespace) -> ObservationPolicy:
    changed = policy
    if args.exclude is not None:
        changed = changed.excluding(tuple(args.exclude))
    if args.only is not None:
        changed = changed.only(tuple(args.only))
    if args.keep_days is not None:
        changed = changed.keeping_for(args.keep_days)
    if args.snapshots:
        changed = changed.reading_structure(True)
    if args.no_snapshots:
        changed = changed.reading_structure(False)
    if args.on:
        changed = changed.enabled()
    if args.off:
        changed = changed.disabled()
    return changed


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
