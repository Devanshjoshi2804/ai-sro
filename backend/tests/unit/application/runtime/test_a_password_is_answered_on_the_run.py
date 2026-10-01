import pytest

from sro.application.context import RequestContext
from sro.application.ports.vault import VaultUnavailable
from sro.application.runtime.answer_password import AnswerPassword
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.execution.account import K_LEASE_TTL
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId
from tests.unit.runtime_support import CTX, TENANT, SteelRun, save_step, steel_run

TYPED = "Hunter2-Not-A-Real-One"


class _Down:
    async def store(self, key: str, value: str) -> None:
        raise VaultUnavailable("the vault is down")


async def _asking_for_a_password() -> tuple[SteelRun, str, AnswerPassword]:
    world = await steel_run(steps=[save_step(status=201)])
    world.driver.shows_sign_in_until_signed = True
    await world.vault.delete(world.account.vault_key("state"))
    await world.vault.delete(world.account.vault_key("password"))
    await world.run_steps.prepare(CTX, world.run_id)
    asking = await world.run_steps.acquire(CTX, world.run_id)
    assert asking
    await world.run_steps.release(CTX, world.run_id)  # the workflow lets go while it waits
    door = AnswerPassword(world.uow, world.vault, world.once, AnswerRun(world.uow, world.durable))
    return world, asking, door


async def _signed_in_after(world: SteelRun, asking: str) -> bool:
    world.clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)  # a person takes minutes
    await world.run_steps.answered(CTX, world.run_id, asking)
    return await world.run_steps.acquire(CTX, world.run_id) == ""


async def test_a_kept_password_goes_to_the_vault_under_the_questions_account() -> None:
    world, asking, door = await _asking_for_a_password()

    await door.execute(CTX, run_id=world.run_id, question_id=asking, value=TYPED, keep=True)

    assert world.vault.secrets[world.account.vault_key("password")] == TYPED
    assert world.durable.answered == [(world.run_id, asking)]
    assert TYPED not in str((await world.saved_run()).progress)
    assert await _signed_in_after(world, asking)


async def test_a_password_for_this_once_is_never_in_the_vault_and_still_signs_the_run_in() -> None:
    world, asking, door = await _asking_for_a_password()

    await door.execute(CTX, run_id=world.run_id, question_id=asking, value=TYPED, keep=False)

    key = world.account.vault_key("password")
    assert TYPED not in world.vault.secrets.values()
    assert world.once.waiting(key, run_id=world.run_id)
    assert await _signed_in_after(world, asking)
    assert not world.once.waiting(key, run_id=world.run_id)
    assert TYPED not in world.vault.secrets.values()


@pytest.mark.parametrize("who", ["a stranger", "another question", "no password asked"])
async def test_nothing_is_stored_when_the_answer_is_not_the_question(who: str) -> None:
    world, asking, door = await _asking_for_a_password()
    ctx, qid = CTX, asking
    if who == "a stranger":
        ctx = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("someone-else"))
    if who == "another question":
        qid = "q_not_this_one"
    if who == "no password asked":
        await world.asks({"id": asking, "kind": "value", "text": "which?"})

    with pytest.raises(Conflict):
        await door.execute(ctx, run_id=world.run_id, question_id=qid, value=TYPED, keep=True)

    key = world.account.vault_key("password")
    assert world.vault.secrets.get(key) is None
    assert not world.once.waiting(key, run_id=world.run_id)
    assert world.durable.answered == []


async def test_a_question_asked_before_it_named_its_account_is_refused_not_guessed() -> None:
    world, asking, door = await _asking_for_a_password()
    await world.asks({"id": asking, "kind": "password", "text": "store a new one"})

    with pytest.raises(Conflict):
        await door.execute(CTX, run_id=world.run_id, question_id=asking, value=TYPED, keep=True)

    assert not world.vault.secrets.get(world.account.vault_key("password"))


async def test_a_vault_that_fails_leaves_the_run_asking_and_a_second_press_works() -> None:
    world, asking, door = await _asking_for_a_password()
    down = AnswerPassword(world.uow, _Down(), world.once, AnswerRun(world.uow, world.durable))

    with pytest.raises(VaultUnavailable):
        await down.execute(CTX, run_id=world.run_id, question_id=asking, value=TYPED, keep=True)

    assert world.durable.answered == []
    await door.execute(CTX, run_id=world.run_id, question_id=asking, value=TYPED, keep=True)
    assert world.durable.answered == [(world.run_id, asking)]


async def test_a_second_press_after_the_answer_stores_nothing_new() -> None:
    world, asking, door = await _asking_for_a_password()
    await door.execute(CTX, run_id=world.run_id, question_id=asking, value=TYPED, keep=True)

    with pytest.raises(Conflict):
        await door.execute(CTX, run_id=world.run_id, question_id=asking, value="other", keep=True)

    assert world.vault.secrets[world.account.vault_key("password")] == TYPED


async def test_an_empty_password_is_refused() -> None:
    world, asking, door = await _asking_for_a_password()

    with pytest.raises(Conflict):
        await door.execute(CTX, run_id=world.run_id, question_id=asking, value="", keep=True)

    assert world.durable.answered == []
