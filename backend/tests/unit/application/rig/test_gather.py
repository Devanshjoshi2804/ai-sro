"""The gather loop against a mailbox that answers.

The plan's own caution is what these are shaped around: the test mails on the
real deployment carry their values inline, so a naive one-message extraction
will appear to work and prove nothing. The case that decides whether this is
built right is a request that says "as discussed" and a value that is in an
EARLIER message -- so that is the first test here, not the last.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any

from sro.application.context import RequestContext
from sro.application.execution.gather import GatherContext
from sro.application.ports.tools import ToolResult, ToolsUnavailable
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer

CTX = RequestContext(tenant_id=TenantId("greyorange"), principal_id=PrincipalId("devansh"))
CODE, DESCRIPTION = "Customer Type", "Customer Type Description"


class _Mailbox:
    """A connector that answers whatever the test put in it, and records what
    it was asked -- per operator, because the port takes one."""

    def __init__(self, answers: dict[str, str]) -> None:
        self._answers = answers
        self.asked: list[tuple[str, str, dict[str, str]]] = []

    @property
    def available(self) -> bool:
        return True

    async def list_tools(self, tenant_id: TenantId, principal_id: PrincipalId, server: str) -> Any:
        return ()

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        self.asked.append((principal_id.value, tool, dict(arguments)))
        key = arguments.get("query") or arguments.get("id") or ""
        if key not in self._answers:
            return ToolResult(text=json.dumps({"messages": []}))
        return ToolResult(text=self._answers[key])


class _Steps:
    """The model, one scripted answer per round."""

    def __init__(self, *answers: dict[str, object]) -> None:
        self._answers = list(answers)
        self.saw: list[str] = []

    async def ask(self, *, evidence: str, **_: object) -> Answer:
        self.saw.append(evidence)
        if not self._answers:
            return Answer(data={"action": "done", "values": [], "why": "nothing left to try"})
        return Answer(data=self._answers.pop(0), cost_usd=0.001)


def _gather(tools: Any, asker: Any) -> GatherContext:
    return GatherContext(tools=tools, asker=asker, model="flash")


async def test_a_value_the_triggering_message_does_not_carry_is_still_found() -> None:
    """The case the plan warns about, and the reason this is the first test.

    The request says "as discussed"; the code is in an earlier message. A
    gather that stopped at the first hit would come back with a description and
    no code, and -- far worse -- a gather that guessed would put a model's
    invention into a warehouse.
    """
    mailbox = _Mailbox(
        {
            "customer type request": json.dumps(
                {"messages": [{"id": "m-2", "subject": "New customer type, as discussed"}]}
            ),
            "m-2": json.dumps(
                {"id": "m-2", "body": "Please raise the new customer type as discussed on Monday."}
            ),
            "customer type Monday": json.dumps(
                {"messages": [{"id": "m-1", "subject": "Monday: codes for the new types"}]}
            ),
            "m-1": json.dumps(
                {"id": "m-1", "body": "The code is ZQ50, description 'Third party'."}
            ),
        }
    )
    asker = _Steps(
        {"action": "search", "query": "customer type request", "why": "find the request"},
        {"action": "read", "message_id": "m-2", "why": "read it"},
        {"action": "search", "query": "customer type Monday", "why": "it points at Monday"},
        {"action": "read", "message_id": "m-1", "why": "the codes should be here"},
        {
            "action": "done",
            "values": [
                {"name": CODE, "value": "ZQ50", "from_message": "m-1", "quoting": "code is ZQ50"},
                {
                    "name": DESCRIPTION,
                    "value": "Third party",
                    "from_message": "m-1",
                    "quoting": "description 'Third party'",
                },
            ],
            "why": "both were in the earlier message",
        },
    )

    got = await _gather(mailbox, asker).execute(
        CTX, job="Create a Customer Type", wanted=[CODE, DESCRIPTION]
    )

    assert got.complete, got.missing
    assert got.values[CODE].value == "ZQ50"
    # The provenance, and it is the point: the value came from the earlier
    # message, not the one that triggered the job.
    assert got.values[CODE].from_message == "m-1"
    # The opening search on the job's own name comes first and finds nothing;
    # everything after it is the model's.
    assert got.looked == (
        "search 'Create a Customer Type'",
        "search 'customer type request'",
        "read m-2",
        "search 'customer type Monday'",
        "read m-1",
    )


async def test_a_value_the_mailbox_does_not_hold_is_said_and_never_guessed() -> None:
    """`write_plan_for` refuses rather than guessing and so does this. A run
    then asks a person, which is far better than a wrong record."""
    mailbox = _Mailbox({"customer type": json.dumps({"messages": []})})
    asker = _Steps(
        {"action": "search", "query": "customer type", "why": "look"},
        {"action": "done", "values": [], "why": "the mailbox has nothing"},
    )

    got = await _gather(mailbox, asker).execute(
        CTX, job="Create a Customer Type", wanted=[CODE, DESCRIPTION]
    )

    assert not got.complete
    assert got.missing == (CODE, DESCRIPTION)
    assert "none of the values" in got.why


async def test_a_value_with_no_message_behind_it_is_dropped_not_carried() -> None:
    """The model reporting a value it cannot point at a message for has
    produced it rather than read it."""
    asker = _Steps(
        {
            "action": "done",
            "values": [{"name": CODE, "value": "ZQ50", "from_message": ""}],
            "why": "I think it is ZQ50",
        }
    )

    got = await _gather(_Mailbox({}), asker).execute(
        CTX, job="Create a Customer Type", wanted=[CODE]
    )

    assert got.missing == (CODE,)
    assert not got.values


async def test_the_mailbox_is_asked_as_the_operator_and_no_one_else() -> None:
    """Each reads their own mail. The port takes the principal and this passes
    it down; a gather that reached another operator's mailbox would be the
    boundary undone one layer up."""
    mailbox = _Mailbox({"x": json.dumps({"messages": []})})
    asker = _Steps(
        {"action": "search", "query": "x", "why": "look"},
        {"action": "done", "values": [], "why": "nothing"},
    )

    await _gather(mailbox, asker).execute(CTX, job="a job", wanted=[CODE])

    assert {who for who, _, _ in mailbox.asked} == {"devansh"}
    assert len(mailbox.asked) == 2, "the opening search and the one the model chose"


async def test_it_stops_looking_rather_than_spending_the_whole_budget() -> None:
    """A loop that can ask six times is a bill. A round that asks for nothing
    cannot be followed by a better one -- the history would be identical and so
    would the next answer -- so it stops."""
    asker = _Steps(
        {"action": "search", "query": "", "why": "I have no query"},
        {"action": "done", "values": [], "why": "unreachable"},
    )

    got = await _gather(_Mailbox({}), asker).execute(CTX, job="a job", wanted=[CODE], rounds=6)

    assert len(asker.saw) == 1, "it kept asking after a round that asked the mailbox nothing"
    assert got.missing == (CODE,)


async def test_a_connector_that_refuses_is_an_observation_not_the_end() -> None:
    """One bad call must not lose the gather. The refusal goes into the history
    and the next round may try a different query."""

    class _Gone(_Mailbox):
        async def call(self, *args: object, **kw: object) -> ToolResult:
            raise ToolsUnavailable("gmail did not answer")

    asker = _Steps(
        {"action": "search", "query": "customer type", "why": "look"},
        {"action": "done", "values": [], "why": "the mailbox is down"},
    )

    got = await _gather(_Gone({}), asker).execute(CTX, job="a job", wanted=[CODE])

    assert got.missing == (CODE,)
    assert len(asker.saw) == 2, "the refusal ended the gather instead of being fed back"
    assert "could not be reached" in asker.saw[1]


async def test_what_was_demonstrated_is_shown_as_a_shape_and_not_offered_as_an_answer() -> None:
    """`seen_values` is what the parameter has been observed taking. A gather
    that copied one would create the demonstration's record again, which is the
    defect the whole replay path exists to have fixed -- so it reaches the
    model as context and the instructions forbid carrying it over."""
    asker = _Steps({"action": "done", "values": [], "why": "nothing"})

    await _gather(_Mailbox({}), asker).execute(
        CTX, job="a job", wanted=[CODE], seen={CODE: ["GGD", "GKB"]}
    )

    shown = json.loads(asker.saw[0])
    assert shown["seen_before"] == {CODE: ["GGD", "GKB"]}


async def test_the_history_shown_to_the_model_is_notes_rather_than_mail() -> None:
    """A mailbox answers with somebody's mail. What the next round is shown is
    a trimmed line per look, because raw accumulation is how this loop would
    poison, distract and confuse itself."""
    body = "x" * 5000
    mailbox = _Mailbox({"q": json.dumps({"messages": [{"id": "m-1", "body": body}]})})
    asker = _Steps(
        {"action": "search", "query": "q", "why": "look"},
        {"action": "done", "values": [], "why": "nothing"},
    )

    await _gather(mailbox, asker).execute(CTX, job="a job", wanted=[CODE])

    second = json.loads(asker.saw[1])
    assert len(second["already_looked_at"]) == 2, "the opening search, then the model's"
    assert all(len(one) < 400 for one in second["already_looked_at"]), (
        "the whole mail went into the prompt"
    )


async def test_the_mailbox_is_always_looked_in_before_anything_is_concluded() -> None:
    """A `done` on round one is a refusal to look, not a conclusion.

    Measured on the deployment 2026-09-16: a run with no values asked the model
    first, the model answered `done` with nothing, and the connector logged no
    request at all. "The mailbox does not hold this" has to be a statement
    about the mailbox.

    So the job's own name is the opening query, and the model's first decision
    is made with results in front of it.
    """
    mailbox = _Mailbox({"Create a Customer Type": json.dumps({"messages": []})})
    asker = _Steps({"action": "done", "values": [], "why": "I have nothing to go on"})

    got = await _gather(mailbox, asker).execute(CTX, job="Create a Customer Type", wanted=[CODE])

    assert [tool for _, tool, _ in mailbox.asked] == ["search_threads"]
    assert got.looked == ("search 'Create a Customer Type'",)
    assert got.missing == (CODE,)
    # And the model was asked with that search already in its history.
    assert "Create a Customer Type" in json.loads(asker.saw[0])["already_looked_at"][0]


async def test_the_reason_the_run_was_started_beats_the_job_name_as_an_opening() -> None:
    """Where something said why the run exists -- a mail that fired it, a
    sentence somebody typed -- that is a better query than the job's title,
    which every run of the job would share."""
    mailbox = _Mailbox({"ZQ50 please": json.dumps({"messages": []})})
    asker = _Steps({"action": "done", "values": [], "why": "nothing"})

    got = await _gather(mailbox, asker).execute(
        CTX, job="Create a Customer Type", wanted=[CODE], because="ZQ50 please"
    )

    assert got.looked[0] == "search 'ZQ50 please'"


async def test_a_look_that_outlasts_a_person_watching_stops_and_says_so() -> None:
    """Measured on the deployment 2026-09-16: a run sat at "Step 0" for three
    and a half minutes because Google answered one round with a 5xx and the
    asker did what it should -- three attempts, a two-second backoff, a
    two-minute ceiling each. `K_ROUNDS` bounds how many times this looks and
    not how long looking takes, and six rounds of that is half an hour of a
    card saying nothing while somebody watches it.
    """

    class _Slow:
        """A model that takes one look and then stops answering."""

        def __init__(self) -> None:
            self.asked = 0

        async def ask(self, **_: object) -> Answer:
            self.asked += 1
            if self.asked > 1:
                await asyncio.sleep(30)
            return Answer(data={"action": "search", "query": "customer type", "why": "look"})

    mailbox = _Mailbox({"customer type": json.dumps({"messages": []})})
    asker = _Slow()

    began = asyncio.get_running_loop().time()
    got = await _gather(mailbox, asker).execute(CTX, job="a job", wanted=[CODE], patience=0.2)
    took = asyncio.get_running_loop().time() - began

    assert took < 5, "the gather waited on a model that was never going to answer"
    assert asker.asked == 2, "it gave up before the round that actually hung"
    assert got.missing == (CODE,)
    assert "ran out of time" in got.why
    # And what it DID look at is still the record of where it got to.
    assert got.looked == ("search 'a job'", "search 'customer type'")


async def test_a_gather_with_no_time_left_asks_nothing_at_all() -> None:
    """The budget is checked before the call, not after it: a round begun with
    nothing left is a model call nobody is waiting for any more."""
    asker = _Steps({"action": "search", "query": "x", "why": "look"})

    got = await _gather(_Mailbox({}), asker).execute(CTX, job="a job", wanted=[CODE], patience=-1.0)

    assert asker.saw == [], "it asked a model after its own deadline"
    assert got.missing == (CODE,)
