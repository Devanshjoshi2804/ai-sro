from sro.infrastructure.steel.driver import best_frame


def test_a_strict_match_outranks_a_repair_in_another_frame() -> None:
    assert best_frame([("shell", "repair"), ("screen", "component")]) == "screen"


def test_a_lone_repair_is_the_frame_when_nothing_matched_strictly() -> None:
    assert best_frame([("screen", "repair")]) == "screen"


def test_two_strict_matches_name_no_frame() -> None:
    assert best_frame([("a", "css_path"), ("b", "attributes"), ("c", "repair")]) is None


def test_nothing_found_names_no_frame() -> None:
    assert best_frame([]) is None
