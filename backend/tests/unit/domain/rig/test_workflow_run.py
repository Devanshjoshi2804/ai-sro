from sro.domain.execution.workflow_run import OUTCOMES, VERDICTS, new_run_id


def test_a_run_id_has_the_shape_the_other_ids_have() -> None:
    run_id = new_run_id()
    assert run_id.startswith("run_")
    assert len(run_id) == len("run_") + 32


def test_the_vocabularies_are_closed() -> None:
    assert set(OUTCOMES) == {"running", "held", "stopped", "refused", "aborted", "failed"}
    assert set(VERDICTS) == {
        "held",
        "failed",
        "unclear",
        "withheld",
        "refused",
        "skipped",
        "awaiting",
        "done_by_operator",
    }
