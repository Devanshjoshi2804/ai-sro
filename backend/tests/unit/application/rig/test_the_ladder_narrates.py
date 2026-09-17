"""The ladder says what it did.

Not a test of any job: a run that leaves nothing behind but a truncated
sentence on a row is one nobody can debug, whatever the workflow. Four separate
faults over 2026-09-15 to 17 each arrived as the same few words and each cost a
deploy-and-rerun cycle to tell apart.
"""

import logging

import pytest

pytestmark = pytest.mark.anyio


async def test_a_run_says_which_rungs_it_built_and_what_each_one_did(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from sro.domain.execution.planning import Answer
    from tests.unit.application.rig.test_runner import (
        FakeAsker,
        FakeChannel,
        _fixture,
        _looks,
        _performed,
        _plan,
        _ran,
        _workflow,
    )

    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel({**_looks(4), "ui.perform": [_performed()] * 3})
    asker = FakeAsker(
        _plan("type", "SAID"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    with caplog.at_level(logging.INFO, logger="sro.application.execution.run_workflow"):
        run = await _ran(uow, workflow, channel=channel, asker=asker, values={}, earned=True)

    said = "\n".join(one.getMessage() for one in caplog.records)
    assert run.id in said, "a line nobody can tie to a run is a line nobody can grep"
    # The rungs BY NAME, not the word "rungs": every assertion here names
    # something the ladder computed, because a format string satisfies an
    # assertion about its own literals and says nothing.
    assert "rungs evidence then" in said, said
    # What a rung planned, as a kind and a shape.
    assert "planned ui.perform" in said, said
    assert "by component" in said or "by css_path" in said, said
    # What the browser answered.
    assert "ok matched_by=" in said, said
    # And what it concluded, with what it cost.
    assert "held by" in said and "$0." in said, said
    # And the values typed into the warehouse are not in it. A log outlives the
    # run; a customer's payload has no business in one.
    assert "SAID" not in said, said
