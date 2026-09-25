from sro.domain.skill.signing_in import (
    PageSignals,
    a_navigation,
    a_sign_in_page,
    asks_for_a_code,
    expired,
)

AUTHORIZE = (
    "https://idp.example/authorize?response_type=code&client_id=wms"
    "&redirect_uri=https%3A%2F%2Fwms.example%2Fcb&state=s1"
)


def _after(*hops: str, now: str = "https://wms.example/app") -> PageSignals:
    return PageSignals(now, visited=tuple(a_navigation(one) for one in (AUTHORIZE, *hops)))


def test_a_password_form_on_any_host_is_a_sign_in_page() -> None:
    assert a_sign_in_page(PageSignals("https://anything.example/x", password=True))


def test_a_username_alone_is_not_a_sign_in_page() -> None:
    assert not a_sign_in_page(
        PageSignals("https://wms.example/users/new", autocomplete=frozenset({"username"}))
    )


def test_a_new_password_alone_is_not_a_sign_in_page() -> None:
    assert not a_sign_in_page(
        PageSignals("https://wms.example/users/new", autocomplete=frozenset({"new-password"}))
    )


def test_a_current_password_token_is_a_sign_in_page() -> None:
    assert a_sign_in_page(
        PageSignals("https://idp.example/u", autocomplete=frozenset({"current-password"}))
    )


def test_a_path_that_looks_like_a_login_is_not_one_by_itself() -> None:
    assert not a_sign_in_page(PageSignals("https://wms.example/oauth2/settings"))


def test_a_pass_through_single_sign_on_is_inside_its_round_trip() -> None:
    assert a_sign_in_page(_after(now="https://idp.example/sso/hop"))


def test_the_round_trip_ends_at_a_query_code_return() -> None:
    assert not a_sign_in_page(_after("https://wms.example/cb?code=c&state=s1"))


def test_the_round_trip_ends_at_a_fragment_return_whose_fragment_the_log_never_sees() -> None:
    assert not a_sign_in_page(_after("https://wms.example/cb"))


def test_the_round_trip_ends_at_a_form_post_return_with_no_query() -> None:
    assert not a_sign_in_page(_after(now="https://wms.example/cb"))


def test_the_round_trip_ends_at_an_error_return() -> None:
    assert not a_sign_in_page(_after("https://wms.example/cb?error=login_required&state=s1"))


def test_an_app_url_carrying_code_and_state_does_not_end_the_round_trip() -> None:
    assert a_sign_in_page(_after(now="https://wms.example/locations?code=A1&state=open"))


def test_a_lost_navigation_log_is_never_read_as_outside_a_round_trip() -> None:
    assert a_sign_in_page(PageSignals("https://idp.example/sso/hop", visited=None))


def test_a_logged_navigation_keeps_parameter_names_and_only_the_return_page() -> None:
    back = a_navigation("https://wms.example/cb?code=SECRET&state=s1#access_token=T")
    asked = a_navigation(
        "https://idp.example/authorize?response_type=code&client_id=wms&login_hint=bob"
        "&redirect_uri=https%3A%2F%2Fwms.example%2Fcb%3Fk%3Dv&state=s1"
    )

    assert back == "https://wms.example/cb?code&state"
    assert asked == (
        "https://idp.example/authorize?response_type&client_id&login_hint"
        "&redirect_uri=https%3A%2F%2Fwms.example%2Fcb&state"
    )


def test_a_one_time_code_asks_for_a_person() -> None:
    otp = PageSignals("https://idp.example/mfa", autocomplete=frozenset({"one-time-code"}))

    assert a_sign_in_page(otp) and asks_for_a_code(otp)


def test_a_sign_in_page_away_from_the_recorded_page_is_an_expired_session() -> None:
    signals = PageSignals("https://idp.example/login", password=True)

    assert expired(signals, "https://wms.example/app")


def test_a_password_form_on_the_page_the_step_was_recorded_on_is_not_expiry() -> None:
    change_password = PageSignals("https://wms.example/users/42/password", password=True)

    assert not expired(change_password, "https://wms.example/users/7/password")


def test_a_plain_page_away_from_the_recorded_page_is_not_expiry() -> None:
    assert not expired(PageSignals("https://wms.example/other"), "https://wms.example/app")
