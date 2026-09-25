"""The one-shot QA vault key migration.

S1 changed vault keys from `{tenant}/{credential origin}/password` to
`{tenant}/{credential origin}/{encoded username}/password`, built by
`Account.vault_key`. QA's passwords are still stored under the old key --
recorded before S1 -- and the new scheme has no fallback to it, so a sign-in
job that used to find its password now finds nothing.

This script reads the old key for each recorded sign-in job and writes it
under the new key it would use, built the one way `Account.vault_key` builds
it: never a hand-assembled string. It never deletes anything unless told to,
never prints a value, and running it twice changes nothing the first run
didn't already change.
"""

from __future__ import annotations

from scripts.migrate_vault_keys import migrate

from sro.application.observation.mining_pass import decide_sign_ins
from sro.domain.execution.account import Account
from sro.domain.execution.secrets import secret_key_of
from sro.domain.observation.gesture import Action, Gesture, PageMark, Target
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeCredentialVault, FakeUnitOfWork

IDP = "https://login.example.com"
LANDS = "https://wms.example.com"
OLD_VALUE = "s3cr3t-hunter2"


def _gesture(gesture_id: str, stream: str, at: float, origin: str, action: Action) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=f.TENANT.value,
        stream_id=stream,
        batch_id="b",
        at=at,
        url=f"{origin}/page",
        system=origin,
        tab_id=1,
        frame_url=None,
        action=action,
    )


def _sign_in(name: str, *, user: str | None, at: float = 1.0) -> dict[str, Gesture]:
    typed = Target(tag="input", name="username")
    secret = Target(tag="input", name="password", secret=True)
    submit = _gesture(f"{name}-go", name, at + 2, IDP, Action(kind="click", at=at + 2))
    submit.page_events.append(PageMark(at=at + 2.5, page_kind="load", url=f"{LANDS}/home"))
    return {
        f"{name}-user": _gesture(
            f"{name}-user", name, at, IDP, Action(kind="type", at=at, value=user, target=typed)
        ),
        f"{name}-pass": _gesture(
            f"{name}-pass", name, at + 1, IDP, Action(kind="type", at=at + 1, target=secret)
        ),
        f"{name}-go": submit,
        f"{name}-there": _gesture(
            f"{name}-there", name, at + 3, LANDS, Action(kind="click", at=at + 3)
        ),
    }


def _job(
    name: str, *, cites: tuple[str, ...] = ("user", "pass", "go"), signs_in: bool | None = True
) -> Workflow:
    return Workflow(
        id=f"wfl_{name}",
        tenant=f.TENANT.value,
        title=name,
        narrative="n",
        steps=[
            Step(order=n, says="s", system=None, cites=[f"{name}-{one}"])
            for n, one in enumerate(cites)
        ],
        signs_in=signs_in,
    )


OLD_KEY = secret_key_of(f.TENANT.value, "login.example.com", "password")


async def _world(
    jobs: list[Workflow], gestures: dict[str, Gesture], *, old_value: str | None = OLD_VALUE
) -> tuple[FakeUnitOfWork, FakeCredentialVault]:
    uow = FakeUnitOfWork()
    for job in jobs:
        await uow.workflows.save(job)
    await uow.gestures.add_gestures(tuple(gestures.values()))
    vault = FakeCredentialVault()
    if old_value is not None:
        await vault.store(OLD_KEY, old_value)
    return uow, vault


async def test_a_recorded_sign_in_copies_the_old_key_to_the_new_one() -> None:
    job = _job("a")
    uow, vault = await _world([job], _sign_in("a", user="alice"))

    lines = await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=False)

    new_key = Account.of(f.TENANT.value, "login.example.com", "alice").vault_key("password")
    assert await vault.get(new_key) == OLD_VALUE
    assert await vault.get(OLD_KEY) == OLD_VALUE  # the old key is kept
    assert any("copied" in line and job.id in line for line in lines)


async def test_a_job_with_no_recorded_username_is_skipped() -> None:
    job = _job("b", cites=("pass", "go"))  # no username step cited
    uow, vault = await _world([job], _sign_in("b", user="alice"))

    lines = await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=False)

    assert vault.secrets == {OLD_KEY: OLD_VALUE}  # nothing new written
    assert any("skipped" in line and "username" in line for line in lines)


async def test_a_job_with_no_old_key_is_skipped() -> None:
    job = _job("c")
    uow, vault = await _world([job], _sign_in("c", user="carol"), old_value=None)

    lines = await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=False)

    assert vault.secrets == {}
    assert any("skipped" in line and "old key" in line for line in lines)


async def test_dry_run_writes_nothing() -> None:
    job = _job("d")
    uow, vault = await _world([job], _sign_in("d", user="dave"))

    await migrate(lambda: uow, vault, [f.TENANT], apply=False, delete_old=False)

    assert vault.secrets == {OLD_KEY: OLD_VALUE}


async def test_running_it_twice_changes_nothing_the_first_run_did_not() -> None:
    job = _job("e")
    uow, vault = await _world([job], _sign_in("e", user="erin"))

    await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=False)
    after_first = dict(vault.secrets)

    lines = await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=False)

    assert vault.secrets == after_first
    assert any("already migrated" in line for line in lines)


async def test_delete_old_only_removes_the_old_key_once_the_new_one_exists() -> None:
    job = _job("f")
    uow, vault = await _world([job], _sign_in("f", user="frank"))

    await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=False)
    await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=True)

    assert await vault.get(OLD_KEY) is None
    new_key = Account.of(f.TENANT.value, "login.example.com", "frank").vault_key("password")
    assert await vault.get(new_key) == OLD_VALUE


async def test_no_line_ever_prints_the_secret_value() -> None:
    job = _job("g")
    uow, vault = await _world([job], _sign_in("g", user="gale"))

    lines = await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=True)

    assert all(OLD_VALUE not in line for line in lines)


async def test_a_job_the_quiet_sweep_marked_is_moved_by_the_dry_run() -> None:
    job = _job("h", signs_in=None)
    uow, vault = await _world([job], _sign_in("h", user="hana"))

    before = await migrate(lambda: uow, vault, [f.TENANT], apply=False, delete_old=False)
    assert await decide_sign_ins(uow, f.TENANT, await uow.workflows.undecided()) == 1
    after = await migrate(lambda: uow, vault, [f.TENANT], apply=False, delete_old=False)

    assert not any("would copy" in line for line in before)
    assert any("1 job(s) not yet decided" in line for line in before)
    assert any("would copy" in line and job.id in line for line in after)
    assert not any("not yet decided" in line for line in after)


async def test_old_keys_are_kept_while_any_job_of_the_tenant_is_undecided() -> None:
    """The old key is per origin, not per job: deleting it once job `i` is
    copied would leave an undecided sign-in job on the same origin with no
    password to be moved to it once it is decided."""
    decided, waiting = _job("i"), _job("j", signs_in=None)
    uow, vault = await _world(
        [decided, waiting], _sign_in("i", user="ivy") | _sign_in("j", user="jo", at=5000.0)
    )

    lines = await migrate(lambda: uow, vault, [f.TENANT], apply=True, delete_old=True)

    assert await vault.get(OLD_KEY) == OLD_VALUE
    assert any("not deleting old keys" in line and "not yet decided" in line for line in lines)
    new_key = Account.of(f.TENANT.value, "login.example.com", "ivy").vault_key("password")
    assert await vault.get(new_key) == OLD_VALUE
