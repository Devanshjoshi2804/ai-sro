"""The nightly reading, and the one thing it must not do: stop early.

`sro.cli.read_cron` is the only caller that reads more than one tenant in a
row, so it is the only place where one tenant's refusal can cost another
tenant its reading. That is what these cover; the argparse wrapper around it
is left to argparse, as in `observe.py` and `mint.py`.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from sro.application.context import RequestContext
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.cli import read_cron


class _Door:
    """One `ReadGestures.execute`, scripted per tenant."""

    def __init__(self, script: dict[str, list[object]]) -> None:
        self._script = script
        self.asked: list[str] = []

    async def execute(self, ctx: RequestContext) -> int:
        tenant = ctx.tenant_id.value
        self.asked.append(tenant)
        answer = self._script[tenant].pop(0)
        if isinstance(answer, Exception):
            raise answer
        assert isinstance(answer, int)
        return answer


class _Container:
    def __init__(self, door: _Door) -> None:
        self._door = door

    def read_gestures(self) -> _Door:
        return self._door


_Install = Callable[[dict[str, list[object]]], "_Door"]


@pytest.fixture
def door(monkeypatch: pytest.MonkeyPatch) -> _Install:
    """`build_container` reaches for a database and a model key; neither is
    this module's business."""

    def _install(script: dict[str, list[object]]) -> _Door:
        made = _Door(script)
        monkeypatch.setattr(read_cron, "build_container", lambda: _Container(made))
        return made

    return _install


async def test_a_tenant_that_breaks_does_not_cost_the_next_tenant_its_reading(
    door: _Install,
) -> None:
    made = door({"acme": [RuntimeError("evidence is a mess")], "new": [3, 0]})

    code = await read_cron._run(["acme", "new"])

    assert made.asked[0] == "acme"
    assert "new" in made.asked, "the tenant after the broken one was never read"
    assert code == 1, "something broke, and cron is owed a non-zero exit to say so"


async def test_a_tenant_over_its_budget_is_not_a_broken_run(door: _Install) -> None:
    """`OverCap` means the cap worked. A nightly job that exits non-zero for
    that teaches whoever reads the exit code to stop reading it."""
    door({"acme": [OverCap("$5.01 of $5.00")], "new": [1, 0]})

    code = await read_cron._run(["acme", "new"])

    assert code == 0


async def test_a_deployment_with_no_model_key_is_a_broken_run(door: _Install) -> None:
    door({"acme": [AskerUnavailable("no key")]})

    assert await read_cron._run(["acme"]) == 1


async def test_passes_repeat_until_one_finds_nothing_left(door: _Install) -> None:
    """The point of the loop: 200 a pass, and a night's capture can be more.
    Three passes here, and the run reports what all three read together."""
    made = door({"acme": [200, 200, 17, 0]})

    assert await read_cron._run(["acme"]) == 0
    assert made.asked == ["acme"] * 4


async def test_the_repeat_is_bounded_so_a_pass_that_never_drains_ends(
    door: _Install, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pass that always claims progress would otherwise read forever."""
    monkeypatch.setattr(read_cron, "MAX_PASSES", 4)
    made = door({"acme": [1] * 10})

    assert await read_cron._run(["acme"]) == 0
    assert len(made.asked) == 4
