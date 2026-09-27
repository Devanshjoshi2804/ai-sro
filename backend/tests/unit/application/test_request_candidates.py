import json

from sro.application.chat.candidates import candidate_of, chore_named, rank_jobs
from sro.application.chat.understand import understand
from sro.application.skill.job_facts import JobFacts
from sro.domain.execution.compiled import Compiled, Reason
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import FakeAsker

OK = Compiled(True, (), {})


def _facts(
    id_: str,
    title: str,
    parameters: int = 1,
    compiled: Compiled = OK,
    *,
    signs_in: bool | None = None,
) -> JobFacts:
    step = Step(order=0, says=title, system=None, cites=["ges_0"])
    job = Workflow(
        id=id_,
        tenant="acme",
        title=title,
        narrative="",
        steps=[step],
        parameters=[{"name": f"Field {n}"} for n in range(parameters)],
        signs_in=signs_in,
    )
    return JobFacts(job, {}, {}, (), (), compiled)


def test_duplicates_hide_behind_the_copy_with_the_most_parameters() -> None:
    """The real store: two 0-parameter 'Create a Customer Type' copies beside
    the 4-parameter canonical job. Only the canonical one is offered."""
    facts = [
        _facts("wfl_a", "Create a Customer Type", parameters=0),
        _facts("wfl_b", "Create a customer type", parameters=4),
        _facts("wfl_c", "Create a Customer Type", parameters=0),
        _facts("wfl_d", "Receive a shipment"),
    ]

    ranked = [one.workflow.id for one in rank_jobs("new customer type GT7", facts)]

    assert ranked == ["wfl_b", "wfl_d"]


def test_between_copies_alike_the_one_with_more_held_runs_is_canonical() -> None:
    facts = [_facts("wfl_a", "Log Out"), _facts("wfl_b", "Log Out")]
    ranked = rank_jobs("log out", facts, held={"wfl_b": 3, "wfl_a": 1})
    assert [one.workflow.id for one in ranked] == ["wfl_b"]


def test_the_copy_with_the_most_parameters_is_canonical_even_when_it_cannot_run() -> None:
    """Amendment item 7: most parameters, then most held runs. Runnability never
    picks the canonical copy: a blocked 4-parameter job is answered with why,
    never replaced by a 0-parameter copy that replays demonstrated values. C1's
    ruling keeps a job that cannot run a candidate."""
    broken = Compiled(False, (Reason("field_gone", 0, "x"),), {})
    facts = [
        _facts("wfl_a", "Create a Customer Type", parameters=4, compiled=broken),
        _facts("wfl_b", "Create a Customer Type", parameters=0),
        _facts("wfl_w", "Create a Work Area", compiled=broken),
    ]
    ranked = [one.workflow.id for one in rank_jobs("create a work area", facts)]
    assert ranked == ["wfl_w", "wfl_a"]


def test_a_sign_in_is_never_a_candidate_and_a_request_naming_only_one_is_that_chore() -> None:
    facts = [
        _facts("wfl_kc", "Log in to Keycloak", signs_in=True),
        _facts("wfl_ct", "Create a Customer Type"),
    ]
    assert [one.workflow.id for one in rank_jobs("log in to keycloak", facts)] == ["wfl_ct"]
    named = chore_named("log in to keycloak please", facts)
    assert named is not None and named.workflow.id == "wfl_kc"
    assert chore_named("log in and create customer type GT7", facts) is None


def test_only_the_top_k_are_offered() -> None:
    facts = [_facts(f"wfl_{n}", f"Job number {n}") for n in range(20)]
    assert len(rank_jobs("job", facts, k=8)) == 8


async def test_the_reader_is_given_the_candidates_the_thread_and_the_standing_question() -> None:
    asker = FakeAsker(Answer(data={"job": None, "sure": False, "values": []}))
    candidate = candidate_of(_facts("wfl_a", "Create a Customer Type"))

    await understand("use GT7 please", [candidate], asker, question="What should Customer Type be?")

    evidence = str(asker.asked[0]["evidence"])
    assert json.loads(evidence.split("\n\n", 1)[0]) == {"question": "What should Customer Type be?"}
    assert '<untrusted name="thread">\nuse GT7 please\n</untrusted>' in evidence
    assert "wfl_a" in evidence.split('<untrusted name="candidates">', 1)[1]


async def test_a_reading_that_breaks_the_schema_is_no_job() -> None:
    asker = FakeAsker(Answer(data={"job": "wfl_a"}))
    got = await understand("x", [candidate_of(_facts("wfl_a", "A"))], asker)
    assert got.workflow_id is None


async def test_no_candidate_is_a_reading_of_nothing_and_asks_no_model() -> None:
    asker = FakeAsker()
    got = await understand("x", [], asker)
    assert got.workflow_id is None and got.answer.data == {} and asker.asked == []
