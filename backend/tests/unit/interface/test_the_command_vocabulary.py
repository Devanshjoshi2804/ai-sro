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
from sro.interface.http.schemas import WorkflowRunModel, WorkflowRunStepModel

_SENDERS = ("run_workflow.py", "verify.py", "plan_step.py", "vision_step.py")
"""The files that put a command on the wire. Narrow on purpose: a `kind=`
elsewhere in the package is a different word -- a trigger kind, a gesture kind
-- and reading those in would make this test about vocabulary in general
rather than about this one wire."""


def _senders() -> Path:
    """`src/sro/application/execution`, found by walking up.

    A fixed `parents[N]` is this file's own depth in the tree, which makes
    moving the test a silent failure -- and the mutation sweep runs the suite
    from a copy one level down, where the count lands somewhere else entirely.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        found = parent / "src/sro/application/execution"
        if found.is_dir():
            return found
    raise AssertionError(f"no backend source above {here}")


def _extension(name: str, *, where: str = "src/background") -> str:
    """Found by walking up rather than by counting directories: the mutation
    sweep runs this suite from a copy of the backend one level down, and a
    fixed `parents[N]` lands somewhere with no extension beside it."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        source = parent / "new-chrome-extension" / where / name
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
    senders = _senders()
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


def test_the_extension_answers_with_every_field_this_backend_reads() -> None:
    """The other direction of the same wire, and the quieter failure.

    A kind that goes missing is loud: the browser says `not_actionable` and the
    step fails. A reply FIELD that goes missing is silent. `status` is what
    `belts.status_of` reads to settle a write by rung 1; without it the step
    falls through to a screenshot and a model, `state_verified` is false, and
    the job never earns the right to write unattended -- correctly driven
    forever, and never trusted. Nothing would go red anywhere.

    A canary and not a contract: it checks the NAME appears where the extension
    builds its replies, not that it is filled in the right case. That is enough
    to catch a rename, which is the way this drifts.
    """
    read: set[str] = set()
    senders = _senders()
    for name in (*_SENDERS, "../../domain/execution/belts.py"):
        body = (senders / name).read_text("utf-8")
        read |= set(re.findall(r'result\.get\("([a-z_]+)"\)', body))
        read |= set(re.findall(r'result\["([a-z_]+)"\]', body))
    assert "status" in read and "body" in read, "the two the state belts stand on"

    answers = _extension("commands.js") + _extension("in-page.js")
    named = set(re.findall(r"\b([a-z_]+):", answers))
    assert read <= named, f"the extension names no {sorted(read - named)} in any reply"


def test_the_panel_reads_a_run_by_fields_the_backend_really_answers_with() -> None:
    """One level up the same wire: the run's JSON rather than the command's.

    `api.rigRun` maps the backend's row onto the panel's own words -- `outcome`
    to `status`, `{order, verdict}` to `{index, outcome}` -- and that mapping
    layer is kept deliberately (see the spec's phase 5 amendment). What is not
    deliberate is it reading a field this backend does not answer with: the
    card then draws a blank where the step's verdict goes, on a run somebody is
    watching, and no test anywhere goes red.

    Against the Pydantic models rather than `frontend/openapi.json`, which is
    generated and can be stale: the models are what the route really returns.
    """
    body = _extension("api.js", where="src/background")
    start = body.index("rigRun:")
    reading = body[start : body.index("\n  },", start)]

    for prefix, model in (("run", WorkflowRunModel), ("step", WorkflowRunStepModel)):
        read = set(re.findall(rf"\b{prefix}\.([a-z_]+)", reading))
        assert read, f"nothing read off the {prefix}: the mapping moved"
        assert read <= set(model.model_fields), (
            f"the panel reads {sorted(read - set(model.model_fields))} off a "
            f"{prefix} and {model.__name__} has no such field"
        )


def test_a_plan_may_name_only_the_kinds_a_model_is_offered() -> None:
    """`KINDS` is what the schema offers the model; `COMMAND_KINDS` is
    everything the runner may send. The first has to stay inside the second, or
    a plan could name a command the wire does not carry."""
    assert KINDS < COMMAND_KINDS
