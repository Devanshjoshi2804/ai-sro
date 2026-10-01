from sro.domain.shared.hosts import origin_of
from tests.unit.runtime_support import CTX, IDP, save_step, steel_run


async def test_a_password_question_says_whose_password_and_where_so_a_ui_stores_the_right_key() -> (
    None
):
    world = await steel_run(steps=[save_step(status=201)])
    world.driver.shows_sign_in_until_signed = True
    await world.vault.delete(world.account.vault_key("state"))
    await world.vault.delete(world.account.vault_key("password"))
    await world.run_steps.prepare(CTX, world.run_id)

    assert await world.run_steps.acquire(CTX, world.run_id) != ""

    asking = world.progress().asking
    assert asking["kind"] == "password"
    assert (asking["origin"], asking["username"], asking["field"]) == (
        origin_of(IDP),
        "clerk",
        "password",
    )
