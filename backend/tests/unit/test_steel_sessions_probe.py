from scripts.steel_sessions import Seen, verdict


def test_two_live_sessions_on_their_own_endpoints_are_sessions() -> None:
    seen = Seen(True, False, True, True, True)
    assert verdict(seen) == "sessions"


def test_one_session_with_isolated_lasting_contexts_is_contexts() -> None:
    seen = Seen(False, True, True, True, False)
    assert verdict(seen) == "contexts"


def test_anything_less_is_one_account_per_container() -> None:
    assert verdict(Seen(False, True, True, False, False)) == "one-per-container"
    assert verdict(Seen(True, True, False, False, True)) == "one-per-container"
