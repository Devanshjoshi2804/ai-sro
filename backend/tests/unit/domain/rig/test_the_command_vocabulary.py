"""The command kinds, held against the extension that has to answer them.

Two halves of one list in two languages: `COMMAND_KINDS` here, a `switch` in
`new-chrome-extension/src/background/commands.js` there. A kind that exists on
one side only is a command the browser answers `not_actionable` to, which the
run reads as a step that could not be done -- on a live run, in front of
somebody, with no test anywhere going red.

This is the same seam that had already drifted once: the backend served a shape
`recognise.js` could never match for weeks, because each side was only ever
read against itself. `test_trim` does this for the redaction word lists and
`scripts/offer-replay.mjs` now does it for shapes; this is the command
vocabulary.
"""

from __future__ import annotations

import re
from pathlib import Path

from sro.domain.execution.planning import COMMAND_KINDS, KINDS

_SENDERS = ("run_workflow.py", "verify.py", "plan_step.py", "vision_step.py")
"""The files that put a command on the wire. Narrow on purpose: a `kind=`
elsewhere in the package is a different word -- a trigger kind, a gesture kind
-- and reading those in would make this test about vocabulary in general
rather than about this one wire."""


def _extension(name: str) -> str:
    """Found by walking up rather than by counting directories: the mutation
    sweep runs this suite from a copy of the backend one level down, and a
    fixed `parents[N]` lands somewhere with no extension beside it."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        source = parent / "new-chrome-extension/src/background" / name
        if source.exists():
            return source.read_text(encoding="utf-8")
    raise AssertionError(f"no extension source above {here}")


def _handled() -> set[str]:
    """Every kind `commands.js` has a case for, from its one dispatch switch."""
    body = _extension("commands.js")
    switch = re.search(r"switch \(command\.kind\) \{(.*?)\n  \}", body, re.DOTALL)
    assert switch, "the command switch moved"
    return set(re.findall(r'case "([a-z._]+)":', switch.group(1)))


def _sent() -> set[str]:
    """Every kind this backend's senders actually name."""
    found: set[str] = set()
    senders = Path(__file__).resolve().parents[4] / "src/sro/application/execution"
    for name in _SENDERS:
        found |= set(re.findall(r'kind="([a-z._]+)"', (senders / name).read_text("utf-8")))
    return found


def test_the_extension_answers_every_command_this_backend_can_send() -> None:
    assert _handled() == set(COMMAND_KINDS), (
        "one side of the wire has a kind the other does not: a command the "
        "browser answers not_actionable to, read by the run as a step that "
        "could not be done"
    )


def test_every_kind_a_sender_names_is_one_this_list_knows_about() -> None:
    """The list is only worth having if it is the whole list. A sender reaching
    for a literal nothing declares would pass the test above while putting a
    word on the wire neither side ever agreed on."""
    assert _sent() <= set(COMMAND_KINDS), f"undeclared: {sorted(_sent() - set(COMMAND_KINDS))}"


def test_a_plan_may_name_only_the_kinds_a_model_is_offered() -> None:
    """`KINDS` is what the schema offers the model; `COMMAND_KINDS` is
    everything the runner may send. The first has to stay inside the second, or
    a plan could name a command the wire does not carry."""
    assert KINDS < COMMAND_KINDS
