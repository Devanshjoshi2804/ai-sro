import json
from dataclasses import replace
from pathlib import Path
from tempfile import mkdtemp
from types import SimpleNamespace

import pytest
from evals.__main__ import arguments
from evals.model import K_COST_TOLERANCE, Case, Report, Scored, gate, report
from evals.redact import redacted, shape
from evals.replay import Replayed
from evals.run import frozen, run_ci, write_candidates
from evals.suites.mining import Mining, request_values
from evals.suites.reader import Reader

from sro.domain.prompts.mine import MINE
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.domain.rig.test_asked_by import _gesture, _job
from tests.unit.fakes import FakeUnitOfWork


def _report(accuracy: float, wrong: float, cost: float) -> Report:
    return Report("mining", "mine", 1, "m", 10, accuracy, wrong, cost, 1.0, 2.0)


def test_the_gate_holds_when_nothing_got_worse() -> None:
    assert gate(_report(0.8, 0.1, 0.02), _report(0.8, 0.1, 0.02)) == []


def test_the_gate_refuses_less_accuracy_more_sure_wrongs_or_more_cost() -> None:
    failed = gate(_report(0.8, 0.1, 0.02), _report(0.7, 0.2, 0.03))
    assert len(failed) == 3


def test_a_report_counts_sure_but_wrong() -> None:
    scored = [
        Scored("a", passed=True, sure=True, cost_usd=0.01, latency_s=1.0),
        Scored("b", passed=False, sure=True, cost_usd=0.01, latency_s=3.0),
        Scored("c", passed=False, sure=False, cost_usd=0.01, latency_s=2.0),
    ]
    got = report("mining", MINE, scored)
    assert (got.cases, round(got.accuracy, 3), round(got.sure_but_wrong, 3)) == (3, 0.333, 0.333)
    assert got.p50_s == 2.0


def test_a_value_becomes_its_shape_and_ids_survive() -> None:
    assert shape("GT-0042") == "AA-9999"
    case = Case(
        id="c1",
        suite="reader",
        input={
            "thread": "please create GT0 and GT1 for bob@acme.example",
            "cites": ["ges_" + "a" * 32],
        },
        expected={"values": {"Customer Type": "GT0"}},
    )
    out = redacted(case)
    assert "GT0" not in str(out.input) and "acme" not in str(out.input)
    assert out.input["cites"] == ["ges_" + "a" * 32]
    thread = str(out.input["thread"])
    assert out.expected["values"] == {"Aaaaaaaa Aaaa": "AA9"}
    assert "AA9 and AA9~2" in thread, "two values with one shape stay two values"


async def test_a_mining_case_passes_when_one_job_covers_most_of_its_cites() -> None:
    ids = [f"ges_{n:032x}" for n in range(5)]
    case = Case(
        id="wfl_x",
        suite="mining",
        input={
            "day": [
                {"id": one, "at": float(n), "evidence": {"id": one}} for n, one in enumerate(ids)
            ],
            "crossings": {},
        },
        expected={"cites": ids},
    )
    answer = {
        "workflows": [{"title": "A job", "steps": [{"order": 0, "says": "x", "cites": ids[:4]}]}]
    }

    scored = await Mining().run(case, Replayed(answer))

    assert scored.passed and scored.sure


async def test_a_mining_case_misses_when_a_value_the_request_asked_for_is_not_a_parameter() -> None:
    """A value the request mail gave and the operator typed is what the next
    request will change. A job that covers the cites but keeps that value as
    fixed step text (Create a Customer Type, mined with no parameters) cannot
    run the next request, so it is a miss."""
    ids = [f"ges_{n:032x}" for n in range(5)]
    case = Case(
        id="wfl_x",
        suite="mining",
        input={
            "day": [
                {"id": one, "at": float(n), "evidence": {"id": one}} for n, one in enumerate(ids)
            ],
            "crossings": {},
        },
        expected={"cites": ids, "values": ["GT0"]},
    )
    step = {"order": 0, "says": "Read email instructions: create GT0", "cites": ids}
    fixed = {"workflows": [{"title": "A job", "steps": [step]}]}
    bound = {
        "workflows": [
            {
                "title": "A job",
                "steps": [step],
                "parameters": [{"name": "Code", "seen_values": ["GT0"]}],
            }
        ]
    }

    missed = await Mining().run(case, Replayed(fixed))
    found = await Mining().run(case, Replayed(bound))

    assert (missed.passed, missed.sure) == (False, True)
    assert found.passed


def test_a_doing_is_expected_to_hold_what_its_job_was_seen_to_vary() -> None:
    """Expected values are the values typed in this doing that any job of the
    same title holds as a parameter: a duplicate mined with no parameters is
    then a miss on its own doing, and the job that varies them passes."""
    typed = ["GT0", "9", "Chilled goods", ""]
    seen = {"GT0", "Chilled goods", "GT1", "priority 9"}
    assert request_values(typed, seen) == ["Chilled goods", "GT0"]
    assert request_values(typed, set()) == []


def test_the_tenant_is_shaped_though_it_is_a_lowercase_word() -> None:
    """Lowercase words are kept as prose; a tenant id is one and names a customer."""
    case = Case(
        id="c1",
        suite="reader",
        input={"jobs": [{"tenant": "acme"}], "said": "acme ships"},
        expected={},
    )
    out = redacted(case, tenant="acme")
    assert "acme" not in str(out.input)
    assert out.input["said"] == "aaaa ships"


GES = [f"ges_{n:032x}" for n in range(6)]
URL = "http://bywms:8080/walmart/orders"


def _workflow() -> Workflow:
    return Workflow(
        id="wfl_" + "c" * 32,
        tenant="greyorange",
        title="Create a Customer Type",
        narrative="the operator created a customer type from a mail",
        systems=["bywms"],
        steps=[
            Step(
                order=0,
                says="type the code GT0",
                system="bywms",
                cites=GES[:2],
                parameters=["Customer Type"],
            )
        ],
        parameters=[
            {"name": "Customer Type", "seen_values": ["GT0", "GT1"]},
            {"name": "Owner", "seen_values": ["testsro"]},
        ],
        shape_key=[["bywms", "type", "Customer Type"]],
        pass_id="pas_" + "e" * 32,
    )


def _reader_case() -> Case:
    job = _workflow()
    field = {
        "labels": [],
        "aliases": [],
        "filled_before": True,
        "kind": "sometimes",
        "limits": {"max_length": None, "options": None, "required_on_screen": None},
    }
    return Case(
        id=job.id,
        suite="reader",
        input={
            "thread": "please create customer type GT2 for testsro at " + URL,
            "candidates": [
                {
                    "id": job.id,
                    "title": job.title,
                    "fields": [
                        {**field, "name": "Customer Type", "seen": ["GT0", "GT1"]},
                        {**field, "name": "Owner", "seen": ["testsro"]},
                    ],
                    "asked_by": ["create GT0 please"],
                }
            ],
        },
        expected={"jobs": [job.id], "values": {"Customer Type": "GT2"}},
        answer={
            "job": job.id,
            "sure": True,
            "also": [],
            "values": [{"field": "Customer Type", "value": "GT2", "quote": "customer type GT2"}],
            "items": [],
        },
    )


def _mining_case() -> Case:
    day = [
        {
            "id": one,
            "at": float(n),
            "evidence": {
                "id": one,
                "system": "bywms",
                "gesture": {"kind": "type", "url": URL, "value": "GT0" if n == 1 else "testsro"},
                "intent": {
                    "act": "types the code",
                    "values_seen": [{"field": "Customer Type", "value": "GT0"}],
                },
            },
        }
        for n, one in enumerate(GES[:5])
    ]
    return Case(
        id="wfl_" + "c" * 32,
        suite="mining",
        input={
            "day": day,
            "crossings": {"GT0": GES[:2], "greyorange": GES[2:4], "login testsro": GES[3:5]},
        },
        expected={"cites": GES[:5], "values": ["GT0"]},
        answer={
            "workflows": [
                {
                    "title": "Create a Customer Type",
                    "systems": ["bywms"],
                    "steps": [
                        {"order": 0, "says": "type GT0", "system": "bywms", "cites": GES[:5]}
                    ],
                    "parameters": [{"name": "Customer Type", "seen_values": ["GT0"]}],
                }
            ]
        },
    )


async def _scores(suite: Mining | Reader, case: Case) -> tuple[bool, bool]:
    got = await suite.run(case, Replayed(case.answer))
    return got.passed, got.sure


async def test_a_redacted_case_loads_and_scores_exactly_as_the_raw_one() -> None:
    for suite, case in ((Reader(), _reader_case()), (Mining(), _mining_case())):
        raw = await _scores(suite, case)
        out = redacted(case, tenant="greyorange")
        assert raw == (True, True)
        assert await _scores(suite, Case.load(out.save(Path(mkdtemp())))) == raw, suite.name


def test_schema_keys_are_never_renamed() -> None:
    out = redacted(_reader_case(), tenant="greyorange")
    candidates = out.input["candidates"]
    assert isinstance(candidates, list)
    (job,) = candidates
    assert set(job) == {"id", "title", "fields", "asked_by"}
    assert set(job["fields"][0]) == {
        "name",
        "labels",
        "aliases",
        "seen",
        "filled_before",
        "kind",
        "limits",
    }


def test_values_hosts_and_paths_are_shaped_whatever_their_case() -> None:
    """A lowercase word is kept only as prose. A typed or seen value, a host, a
    path, the tenant and a crossing are shaped, and so is their every occurrence
    in the prose around them: the mail names the account the operator typed."""
    for case in (_reader_case(), _mining_case()):
        text = json.dumps(redacted(case, tenant="greyorange").__getattribute__("input"))
        for word in ("testsro", "bywms", "walmart", "orders", "greyorange"):
            assert word not in text, (case.suite, word)


def test_a_crossing_key_is_a_value_and_keeps_its_gestures() -> None:
    crossings = redacted(_mining_case(), tenant="greyorange").input["crossings"]
    assert isinstance(crossings, dict)
    assert not {"greyorange", "login testsro"} & set(crossings)
    assert sorted(map(len, crossings.values())) == [2, 2, 2]


class _Refusing:
    async def ask(self, **_: object) -> Answer:
        return Answer(error="RuntimeError: the client has been closed")


async def test_an_errored_call_is_an_error_not_an_unsure_miss() -> None:
    got = await Mining().run(_mining_case(), _Refusing())
    assert got.error and not got.passed
    scored = [got, Scored("b", passed=True, sure=True, cost_usd=0.01, latency_s=1.0)]
    now = report("mining", MINE, scored)
    assert now.errors == 1
    assert gate(None, now) and gate(now, now), "a run with an error neither baselines nor passes"


def test_the_gate_refuses_a_different_case_set() -> None:
    before = replace(_report(0.8, 0.1, 0.02), case_ids=("a", "b"))
    assert gate(before, replace(before, case_ids=("a",)))
    assert gate(before, before) == []


def test_cost_is_gated_with_a_tolerance_for_jitter() -> None:
    before = _report(0.8, 0.1, 0.02)
    assert gate(before, _report(0.8, 0.1, 0.02 * (1 + K_COST_TOLERANCE) * 0.99)) == []
    assert gate(before, _report(0.8, 0.1, 0.02 * (1 + K_COST_TOLERANCE) * 1.01))


async def test_the_case_set_is_built_once_and_then_read() -> None:
    root = Path(mkdtemp())
    built: list[int] = []

    async def build() -> list[Case]:
        built.append(1)
        return [_mining_case()]

    first = await frozen(root, "t", "mining", build)
    again = await frozen(root, "t", "mining", build)
    assert first == again == [replace(_mining_case(), answer=None)]
    assert len(built) == 1


async def test_a_rebuild_retires_the_baseline_and_the_old_answers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A rebuilt case set is a new set: the old baseline could only refuse it,
    and the old answers belong to cases that are gone."""
    root = Path(mkdtemp())

    async def build() -> list[Case]:
        return [_mining_case()]

    await frozen(root, "t", "mining", build)
    results = root / "results" / "t"
    replace(_mining_case(), id="wfl_" + "0" * 32).save(results / "mining")
    (results / "baseline-mining.json").write_text("{}")
    (results / "baseline-reader.json").write_text("{}")

    await frozen(root, "t", "mining", build, rebuild=True)

    assert not (results / "baseline-mining.json").exists()
    assert not (results / "mining").exists()
    assert (results / "baseline-reader.json").exists(), "another suite's baseline stays"
    assert "retired" in capsys.readouterr().out


async def test_candidates_come_only_from_the_current_case_set() -> None:
    root = Path(mkdtemp())

    async def build() -> list[Case]:
        return [_mining_case()]

    await frozen(root, "t", "mining", build)
    results = root / "results" / "t" / "mining"
    _mining_case().save(results)
    replace(_mining_case(), id="wfl_" + "0" * 32).save(results)

    await write_candidates("mining", "t", root=root)

    made = sorted(one.stem for one in (root / "candidates" / "t" / "mining").glob("*.json"))
    assert made == [_mining_case().id]


def test_each_suite_asks_through_the_asker_production_uses_for_its_prompt() -> None:
    patient, plain = object(), object()
    container = SimpleNamespace(asker=plain, mining_asker=lambda: patient)
    assert Mining().asker(container) is patient
    assert Reader().asker(container) is plain


async def test_ci_fails_on_an_empty_set() -> None:
    assert await run_ci(live=False, folder=Path(mkdtemp())) == 1


async def test_a_job_lumping_the_whole_window_is_not_a_find() -> None:
    case = _mining_case()
    noise = [f"ges_{n:032x}" for n in range(100, 120)]
    lumped = {
        "workflows": [
            {
                "title": "Everything",
                "steps": [{"order": 0, "says": "all", "cites": GES[:5] + noise}],
                "parameters": [{"name": "Code", "seen_values": ["GT0"]}],
            }
        ]
    }
    got = await Mining().run(case, Replayed(lumped))
    assert (got.passed, got.sure) == (False, True)


def test_a_limit_is_at_least_one_and_never_a_baseline() -> None:
    for argv in (
        ["run", "--suite", "mining", "--tenant", "t", "--limit", "0"],
        ["run", "--suite", "mining", "--tenant", "t", "--limit", "3", "--baseline"],
    ):
        with pytest.raises(SystemExit):
            arguments(argv)
    assert arguments(["run", "--suite", "mining", "--tenant", "t", "--limit", "3"]).limit == 3


async def test_a_sign_in_job_s_mails_are_no_reader_case() -> None:
    """A sign-in job is never a candidate, so a case expecting it scores as a
    miss the reader could never avoid."""
    uow = FakeUnitOfWork()
    mails = {
        one: replace(
            _gesture(one, said=f"please {one}: customer type GGD for north", at=n), tenant="acme"
        )
        for n, one in enumerate(("m-work", "m-login"))
    }
    async with uow:
        await uow.workflows.save(replace(_job(["m-work"]), id="wfl_work", tenant="acme"))
        await uow.workflows.save(
            replace(_job(["m-login"]), id="wfl_login", tenant="acme", title="Log in", signs_in=True)
        )
        await uow.gestures.add_gestures(tuple(mails.values()))
        await uow.commit()

    cases = await Reader().cases(uow, f.TENANT)

    assert [one.id.split(":")[0] for one in cases] == ["wfl_work"]


async def test_a_chore_is_no_mining_case() -> None:
    """The miner is right to skip a sign-in, so a case expecting one scores a
    miss it could never avoid; the greyorange baseline carried several."""
    uow = FakeUnitOfWork()
    done = {
        one: replace(_gesture(one, said="customer type GGD", at=n), tenant="acme")
        for n, one in enumerate(("m-work", "m-login"))
    }
    async with uow:
        await uow.workflows.save(replace(_job(["m-work"]), id="wfl_work", tenant="acme"))
        await uow.workflows.save(
            replace(_job(["m-login"]), id="wfl_login", tenant="acme", title="Log in", signs_in=True)
        )
        await uow.gestures.add_gestures(tuple(done.values()))
        await uow.commit()

    cases = await Mining().cases(uow, f.TENANT)

    assert [one.id for one in cases] == ["wfl_work"]
