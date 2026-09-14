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

from sro.domain.execution.planning import COMMAND_KINDS, KINDS, LIVE_FETCHABLE_HEADERS
from sro.interface.http.app import create_app
from sro.interface.http.schemas import WorkflowRunModel, WorkflowRunStepModel

_SENDERS = (
    "execution/run_workflow.py",
    "execution/verify.py",
    "execution/plan_step.py",
    "execution/vision_step.py",
    "lookup/run_lookups.py",
)
"""The files that put a command on the wire. Narrow on purpose: a `kind=`
elsewhere in the package is a different word -- a trigger kind, a gesture kind
-- and reading those in would make this test about vocabulary in general
rather than about this one wire.

A RUN is not the only sender any more: a lookup drives the same browser with
the same vocabulary, and a kind it reached for that nothing declares would put
a word on the wire neither side agreed on."""


def _senders() -> Path:
    """`src/sro/application`, found by walking up.

    A fixed `parents[N]` is this file's own depth in the tree, which makes
    moving the test a silent failure -- and the mutation sweep runs the suite
    from a copy one level down, where the count lands somewhere else entirely.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        found = parent / "src/sro/application"
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
    for name in (*_SENDERS, "../domain/execution/belts.py"):
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


def test_every_door_the_extension_knocks_on_is_one_this_app_opens() -> None:
    """Every `/v1/...` path in `api.js`, against the app's own OpenAPI.

    The widest of the checks in this file and the cheapest to keep: a route
    renamed or removed on this side is a 404 in a browser somebody is working
    in, and the extension's own suite cannot see it -- every one of those tests
    fakes `fetch`, so the path it asserts is the path it invented.

    Comments are stripped first. `api.js` names several paths in prose --
    "`/v1/workflow-runs/{id}`, not `/v1/runs/{id}`" is a comment explaining why
    the rig's old door is not this one -- and a test that read those would fail
    over an explanation.
    """
    body = _extension("api.js")
    code = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)

    called = {
        re.sub(r"\$\{[^}]*\}", "{}", path).split("?")[0].rstrip("/")
        for path in re.findall(r'["`](/v1/[^"`\s]*)["`]', code)
    }
    assert called, "no paths found: the way api.js writes a url changed"

    served = {
        re.sub(r"\{[^}]*\}", "{}", path).rstrip("/") for path in create_app().openapi()["paths"]
    }
    # `/v1/shapes${query}` is one door with a query string, not a path
    # parameter: the placeholder at the end is `?device_id=...`.
    missing = sorted(
        path
        for path in called
        if path not in served and not (path.endswith("{}") and path[:-2] in served)
    )
    assert not missing, f"the extension calls {missing}, which this app does not serve"


def test_the_extension_has_a_source_for_every_header_this_backend_asks_for() -> None:
    """A sixth seam, and the narrowest: `LIVE_FETCHABLE_HEADERS` here,
    `LIVE_HEADER_SOURCES` there.

    The backend never sends a struck-out header's value -- it names the header
    and the extension goes and finds it on the page. So a name on this list
    with no source over there is a write that fails with `unreachable` at the
    browser, which `commands.js` is careful to make loud rather than silently
    dropping the header. Loud is still only loud at run time, in front of
    somebody, on a call that was about to write to a warehouse.
    """
    menu = set(re.findall(r'"([a-z-]+)":\s*\w+InPage', _extension("commands.js")))
    assert menu == set(LIVE_FETCHABLE_HEADERS), (
        "one side asks for a header the other cannot find: "
        f"backend {sorted(LIVE_FETCHABLE_HEADERS)}, extension {sorted(menu)}"
    )


def test_a_plan_may_name_only_the_kinds_a_model_is_offered() -> None:
    """`KINDS` is what the schema offers the model; `COMMAND_KINDS` is
    everything the runner may send. The first has to stay inside the second, or
    a plan could name a command the wire does not carry."""
    assert KINDS < COMMAND_KINDS
