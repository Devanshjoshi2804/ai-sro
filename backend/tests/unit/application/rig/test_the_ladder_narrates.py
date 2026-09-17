"""The ladder says what it did.

Not a test of any job: a run that leaves nothing behind but a truncated
sentence on a row is one nobody can debug, whatever the workflow. Four separate
faults over 2026-09-15 to 17 each arrived as the same few words and each cost a
deploy-and-rerun cycle to tell apart.
"""

import logging

import pytest

from sro.application.ports.channel import Reply

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


async def test_a_rescue_that_repeats_a_refused_command_does_not_send_it_again(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Six cents to be told the same thing twice.

    `run_e1ff6362`, the deployment, 2026-09-17 at 17:32. Step 3 planned
    `ui.perform click by component,css_path`, the browser answered
    `control_not_found` naming both locators, and the rescue -- which is given
    `previous_attempt_failed` and exists to plan something ELSE -- planned the
    same two locators. $0.0125, then $0.0453, for the same refusal in the same
    words, and only then did the ladder move down a rung.

    A rule in the runner rather than a sentence in a prompt: a command this
    page has just refused will be refused again, whatever model proposed it and
    whatever job it belongs to.
    """
    from tests.unit.application.rig.test_runner import (
        FakeAsker,
        FakeChannel,
        _fixture,
        _looks,
        _plan,
        _ran,
        _workflow,
    )

    uow = await _fixture()
    workflow = await _workflow(uow)
    channel = FakeChannel(
        {
            **_looks(8),
            # Every attempt is refused the same way, which is the case the
            # rescue exists for and the case it was repeating itself in.
            "ui.perform": [
                Reply(
                    ok=False,
                    error_kind="control_not_found",
                    error_detail="no control matched",
                )
            ]
            * 6,
        }
    )
    # The plan rung and the rescue rung propose the identical command.
    # Plans only: a command the browser refused is never verified, so the
    # asker is asked for the next PLAN rather than for a verdict.
    asker = FakeAsker(*[_plan("click")] * 6)

    with caplog.at_level(logging.INFO, logger="sro.application.execution.run_workflow"):
        await _ran(uow, workflow, channel=channel, asker=asker, values={}, earned=True)

    said = "\n".join(one.getMessage() for one in caplog.records)
    sent = [one for one in channel.sent if one["kind"] == "ui.perform"]
    assert len(sent) == 1, f"it sent the same refused command {len(sent)} times:\n{said}"
    assert "already had refused" in said, said
