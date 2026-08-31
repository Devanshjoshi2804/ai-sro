"""Eight tasks, wired to each other, in a real Chrome.

Every piece of "offer to do the next one" has a test of its own: the panel
offers plain words rather than "teach" (`panel.test.mjs`), a sentence resolves
to a preview (`panel.test.mjs` again), a press promotes and runs a version
(`test_execute_from_preview.py` and friends), a finished run can be called
wrong (`test_a_run_the_operator_called_wrong.py`). None of those tests ever
loads the extension, and none of them presses a real button in a real
`chrome.runtime.sendMessage` round trip. This is the one test that does: an
operator's candidate task, offered on the panel, answered with a sentence,
previewed, pressed once, and the run that comes back offering itself undone --
the whole chain, or nothing here would have caught it if a wire between two of
those pieces were simply missing.

What this test does *not* prove, honestly, and cannot without the real
backend: that a task done three times is really *mined* into a candidate.
Mining (`MineObservations`, `segment()`) reads real observation batches
through real segmentation -- proven in
`tests/unit/application/test_noticing_what_somebody_keeps_doing.py` -- and
this suite's stub is deliberately not that backend (see `conftest.py`'s own
docstring: a browser test here must not need Postgres or MinIO to run).
Nothing in the extension ever calls `POST /v1/candidates/mine` either -- it is
a backend sweep, not a panel action -- so the candidate below is served
exactly the way every other candidate in this suite is (`_CANDIDATES` in
`conftest.py`): canned, standing in for "already mined", with `times_seen: 3`
naming the three doings it is supposed to represent. Calling `/mine` against
this stub would prove only that the stub answers 200 to anything, which is
not a thing worth a test.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

pytestmark = pytest.mark.browser

CANDIDATE_ID = "cnd-lpn-here"
SKILL_ID = "skl-lpn-adjust"
SENTENCE = "Adjust the LPN quantity"


def _service_worker(context: Any) -> Any:
    return (
        context.service_workers[0]
        if context.service_workers
        else context.wait_for_event("serviceworker")
    )


def _extension_page(context: Any, worker: Any) -> Any:
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    return page


def _sign_in(context: Any, worker: Any, api_url: str) -> dict[str, Any]:
    page = _extension_page(context, worker)
    status: dict[str, Any] = page.evaluate(
        """async (apiUrl) => await chrome.runtime.sendMessage(
             {kind: "sign-in", apiUrl, consoleUrl: "", token: "test.token.here",
              label: "browser-test"})""",
        api_url,
    )
    page.close()
    return status


def _panel(context: Any, worker: Any) -> Any:
    """The side panel, opened as a page. Chrome docks it beside a tab in real
    use; a test cannot dock it, and the panel finds the ordinary page in its
    window either way."""
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/panel/panel.html")
    return page


def _wait_for(what: list[Any], count: int = 1, timeout: float = 20.0) -> list[Any]:
    until = time.time() + timeout
    while time.time() < until and len(what) < count:
        time.sleep(0.2)
    return what


@pytest.fixture
def armed(browser: Any, stub: Any) -> Any:
    """A browser signed in. No watches -- this chain has nothing to do with
    mail, and every other test in this file is entitled to a browser that
    only ever asked about candidates and runs."""
    api_url, _ = stub
    worker = _service_worker(browser)
    status = _sign_in(browser, worker, api_url)
    assert status["capturing"] is True, f"the extension did not start: {status}"
    return worker


def test_the_offer_the_sentence_the_press_and_the_undo(
    browser: Any,
    stub: Any,
    armed: Any,
    channel: Any,
    run_previews: list[dict[str, Any]],
    run_wrongs: list[dict[str, Any]],
    resolutions_asked: list[str],
    finish_run: Any,
) -> None:
    """The whole chain, judged the way an operator would meet it: a card that
    says what to do in words they would use, a box that takes a sentence, a
    preview that says what is about to happen before it happens, one press,
    and a card afterwards that says what got made and offers to take it back.

    If any one of the wires this test pulls on had never been connected --
    the offer's button firing nothing, a typed sentence never reaching
    `resolve-intent`, a preview built from the wrong version, a press that
    promotes but never actually starts a run, an undo that reverses nothing
    -- every other test in this codebase would still be green, because each
    of them tests its own end of the wire and never the wire itself.
    """
    api_url, _ = stub
    # A second hostname aliasing the same stub server (Chrome resolves
    # `localhost` to the same loopback address `127.0.0.1` is bound on) --
    # see `_CANDIDATES`'s comment on `cnd-lpn-here` in `conftest.py` for why
    # this candidate is not offered on `127.0.0.1`: another test in this
    # suite already counts exactly one "new" candidate there.
    local_url = api_url.replace("127.0.0.1", "localhost")

    system = browser.new_page()
    system.goto(local_url)

    open_channel = channel()
    panel = _panel(browser, armed)

    # -- the offer: plain words, and never "teach" ---------------------------
    row = panel.locator("#candidates li").first
    row.wait_for(timeout=15_000)
    offered = row.text_content()
    assert "Do the next one" in offered, offered
    assert "teach" not in offered.lower(), offered
    assert CANDIDATE_ID not in offered, "a raw id reached the operator"
    assert "PUT wm/inventory/adjust" not in offered, "the raw signature reached the operator"
    # The plain sentence `plainly()` builds off the signature's own noun,
    # rather than either of those raw strings.
    assert "You've created 3 adjusts here" in offered, offered
    row.get_by_role("button", name="Do the next one").click()

    # -- the sentence ----------------------------------------------------------
    sentence_box = row.locator("input[type=text]").first
    sentence_box.wait_for(timeout=15_000)
    sentence_box.fill(SENTENCE)
    row.get_by_role("button", name="Ask").click()

    # -- a preview lists the steps ----------------------------------------------
    row.get_by_text("Type the LPN barcode").wait_for(timeout=15_000)
    previewed = row.text_content()
    assert "Adjust an LPN quantity" in previewed, previewed
    assert "Type the LPN barcode" in previewed, previewed
    assert "LPN-4471" in previewed, previewed
    assert "Press Save" in previewed, previewed
    # And the screen it will act in. ADR 014's argument that a preview counts
    # as a review rests on a closed list of what the operator read -- the step
    # intents, the resolved value of each parameter, and the starting tab --
    # and the run genuinely navigates there before step one.
    assert "wms.test/inventory/lpn" in previewed, previewed

    # -- one press: the stub receives the write ----------------------------------
    row.get_by_role("button", name="Do it").click()
    _wait_for(run_previews)
    row.get_by_text("started").wait_for(timeout=15_000)

    assert resolutions_asked == [SENTENCE], "the sentence typed in the box never reached resolution"
    assert len(run_previews) == 1, run_previews
    [press] = run_previews
    assert press["skill_id"] == SKILL_ID
    # The values a sentence resolved to -- nothing kept anywhere between the
    # preview and the press, so this is the same `{"lpn": "LPN-4471"}` the
    # preview showed, travelling again.
    assert press["parameters"] == {"lpn": "LPN-4471"}
    assert press["intent"] == SENTENCE
    # The version the preview above was actually drawn from. Without it the
    # backend took `skill.latest`, so any skill carrying a newer RECORDED
    # version had the operator reading one version while another wrote.
    assert press["version"] == 1, press
    run_id = press["run_id"]

    # A run in this system becomes real to the extension only once the
    # backend has asked it, over the command channel, to do something for
    # that run id -- see `commands.js`'s `perform()`, which is what
    # `state.activeRun` and the panel's later "finished" card both key off.
    # This stub is not a real orchestrator (see this file's own docstring),
    # so the test stands in for one here, exactly the way
    # `test_the_extension_in_a_real_chrome.py` already does for every other
    # command-driven behaviour in this suite -- one command, naming the run,
    # over the same channel a real backend would use.
    open_channel.command("cmd_step", "ui.url", {}, run_id=run_id)
    answer = open_channel.answer("cmd_step")
    assert answer["ok"] is True, answer

    # And once that run has actually finished, a real backend would say so.
    finish_run(
        run_id,
        {"lpn": "LPN-4471", "quantity": "4"},
        {
            "skill_id": SKILL_ID,
            # The version the undo was validated against, and what its delete
            # step says it does. Both are on the wire so the card can name what
            # the press is about to remove *before* it is pressed, and so the
            # press runs the version it was offered rather than whatever is
            # newest by the time it lands.
            "version": 1,
            "removes": "Set the LPN quantity back to zero",
            "parameters": {"lpn": "LPN-4471", "quantity": "0"},
        },
    )

    # -- the panel shows what was made -------------------------------------------
    # `RUN_QUIET_MS` in `commands.js` is thirty real seconds, on purpose: a
    # run is not called finished the moment it goes quiet, because the quiet
    # window might land between two of its own steps rather than after the
    # last one. This wait is the cost of proving that real timing rather than
    # a faster one invented for this test.
    made = panel.locator("#cards .card", has_text="Created").first
    made.wait_for(timeout=50_000)
    said = made.text_content()
    assert "LPN-4471" in said, said
    assert "4" in said, said
    # And what pressing "Undo that" would delete, named before it is pressed:
    # the reversal skill's own steps are rendered nowhere else, so without this
    # the one press ADR 014 argues for is a press onto a delete nobody read.
    assert "Set the LPN quantity back to zero" in said, said

    # -- and offers to take it back ------------------------------------------
    undo = panel.get_by_role("button", name="Undo that")
    undo.wait_for(timeout=5_000)
    undo.click()
    _wait_for(run_wrongs)
    _wait_for(run_previews, count=2)
    panel.close()
    system.close()

    assert run_wrongs, "the undo pressed nothing"
    assert run_wrongs[0]["run_id"] == run_id
    assert len(run_previews) == 2, run_previews
    reversal_press = run_previews[1]
    assert reversal_press["skill_id"] == SKILL_ID
    assert reversal_press["parameters"] == {"lpn": "LPN-4471", "quantity": "0"}
    assert reversal_press["intent"] == "Undo that"
    assert reversal_press["version"] == 1, (
        "the undo ran whatever version was newest rather than the one it was offered"
    )
