from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sro.application.observation.mining_pass import evidence_of
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.container import build_container
from sro.domain.execution.account import Account
from sro.domain.execution.secrets import secret_key_of
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.checks import signs_in_to
from sro.domain.skill.signing_in import recorded_login
from sro.domain.skill.workflow import Workflow

PASSWORD = "password"  # noqa: S105 -- a vault field's name, not a value

_BEFORE_THIS_SYSTEM_EXISTED = datetime(2000, 1, 1, tzinfo=UTC)


async def _jobs_and_gestures(
    uow: UnitOfWork, tenant_id: TenantId
) -> tuple[list[Workflow], dict[str, Gesture], int]:
    async with uow:
        known = await uow.workflows.known(tenant_id)
        undecided = sum(1 for job in known if job.signs_in is None)
        jobs = [job for job in known if job.signs_in is True]
        seen = await evidence_of(uow, tenant_id, jobs)
    return jobs, seen, undecided


async def _migrate_job(
    vault: CredentialVault,
    tenant_id: TenantId,
    job: Workflow,
    seen: dict[str, Gesture],
    *,
    apply: bool,
    delete_old: bool,
) -> str:
    label = f"{tenant_id.value}/{job.id}"
    landing = signs_in_to(job, seen)
    if landing is None:
        return f"{label}: skipped -- no recorded landing for this sign-in job"
    recorded = recorded_login(landing[1], [job], seen)
    if recorded is None or not recorded.username:
        return f"{label}: skipped -- no recorded username"
    old_key = secret_key_of(tenant_id.value, recorded.origin, PASSWORD)
    old_value = await vault.get(old_key)
    if old_value is None:
        return f"{label}: skipped -- no old key at {old_key}"
    try:
        account = Account.of(tenant_id.value, recorded.origin, recorded.username)
    except InvariantViolation as refused:
        return f"{label}: skipped -- recorded username is unusable ({refused})"
    new_key = account.vault_key(PASSWORD)

    already = await vault.get(new_key) is not None
    if already:
        line = f"{label}: already migrated ({new_key})"
    else:
        if apply:
            await vault.store(new_key, old_value)
        line = f"{label}: {'copied' if apply else 'would copy'} {old_key} -> {new_key}"

    if delete_old:
        if apply:
            await vault.delete(old_key)
            line += f"; deleted {old_key}"
        else:
            line += f"; would delete {old_key}"
    return line


async def migrate(
    uow_factory: Callable[[], UnitOfWork],
    vault: CredentialVault,
    tenants: Sequence[TenantId],
    *,
    apply: bool,
    delete_old: bool,
) -> list[str]:
    lines: list[str] = []
    for tenant_id in tenants:
        jobs, seen, undecided = await _jobs_and_gestures(uow_factory(), tenant_id)
        if undecided:
            lines.append(
                f"{tenant_id.value}: {undecided} job(s) not yet decided -- "
                "wait for a mining sweep, then run this again"
            )
            if delete_old:
                lines.append(
                    f"{tenant_id.value}: not deleting old keys -- {undecided} job(s) not yet"
                    " decided may sign in with one of them"
                )
        for job in jobs:
            lines.append(
                await _migrate_job(
                    vault,
                    tenant_id,
                    job,
                    seen,
                    apply=apply,
                    delete_old=delete_old and not undecided,
                )
            )
    return lines


async def _run(*, apply: bool, delete_old: bool) -> list[str]:
    container = build_container()
    async with container.unit_of_work() as uow:
        tenants = await uow.gestures.tenants_since(_BEFORE_THIS_SYSTEM_EXISTED)
    return await migrate(
        container.unit_of_work, container.vault, tenants, apply=apply, delete_old=delete_old
    )


def main() -> int:
    parsing = argparse.ArgumentParser(description=__doc__)
    parsing.add_argument("--apply", action="store_true", help="write; the default only prints")
    parsing.add_argument("--dry-run", action="store_true", help="print only; the default")
    parsing.add_argument(
        "--delete-old", action="store_true", help="also remove the old key (run only after QA-1)"
    )
    args = parsing.parse_args()
    apply = args.apply and not args.dry_run
    for line in asyncio.run(_run(apply=apply, delete_old=args.delete_old)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
