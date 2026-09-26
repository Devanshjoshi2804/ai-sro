from evals.model import Case, Report, Scored, gate, report
from evals.redact import redacted, shape
from evals.replay import Replayed
from evals.suites.mining import Mining, request_values

from sro.domain.prompts.mine import MINE


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


async def test_a_mining_case_misses_when_a_value_from_two_systems_is_not_a_parameter() -> None:
    """A value typed in the mail and again in the app is what the request asked
    for. A job that covers the cites but keeps that value as fixed step text
    (Create a Customer Type, mined with no parameters) cannot run the next
    request, so it is a miss."""
    ids = [f"ges_{n:032x}" for n in range(5)]
    case = Case(
        id="wfl_x",
        suite="mining",
        input={
            "day": [
                {"id": one, "at": float(n), "evidence": {"id": one}} for n, one in enumerate(ids)
            ],
            "crossings": {"GT0": [ids[0], ids[3]]},
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


async def test_a_mining_case_expects_the_crossing_values_on_its_own_cites() -> None:
    ids = [f"ges_{n:032x}" for n in range(3)]
    crossings = {"GT0": [ids[0], ids[2]], "elsewhere": ["ges_" + "f" * 32, "ges_" + "e" * 32]}
    assert request_values(ids, crossings) == ["GT0"]
