from sro.domain.execution.learned_step import LearnedStep, changed_by


def test_the_same_locator_found_in_another_frame_is_a_change() -> None:
    was = LearnedStep(2, "component", "#save", "sight", frame_path='[{"index": 0, "url": "/a"}]')
    now = LearnedStep(2, "component", "#save", "sight", frame_path='[{"index": 1, "url": "/b"}]')

    assert [one.about for one in changed_by(was, now)] == ["locator"]
