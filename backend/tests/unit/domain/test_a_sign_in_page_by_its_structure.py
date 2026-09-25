from sro.domain.skill.signing_in import PageSignals, a_sign_in_page, asks_for_a_code

AUTHORIZE = (
    "https://idp.example/authorize?response_type=code&client_id=wms"
    "&redirect_uri=https%3A%2F%2Fwms.example%2Fcb&state=s1"
)


def test_a_password_form_on_any_host_is_a_sign_in_page() -> None:
    assert a_sign_in_page(PageSignals("https://anything.example/x", password=True))


def test_an_identifier_first_page_is_a_sign_in_page() -> None:
    assert a_sign_in_page(
        PageSignals("https://idp.example/u", autocomplete=frozenset({"username"}))
    )


def test_a_path_that_looks_like_a_login_is_not_one_by_itself() -> None:
    assert not a_sign_in_page(PageSignals("https://wms.example/oauth2/settings"))


def test_a_pass_through_single_sign_on_is_inside_its_round_trip() -> None:
    hopping = PageSignals("https://idp.example/sso/hop", visited=(AUTHORIZE,))

    assert a_sign_in_page(hopping)


def test_the_round_trip_ends_at_the_code_return() -> None:
    back = PageSignals(
        "https://wms.example/app", visited=(AUTHORIZE, "https://wms.example/cb?code=c&state=s1")
    )

    assert not a_sign_in_page(back)


def test_a_one_time_code_asks_for_a_person() -> None:
    otp = PageSignals("https://idp.example/mfa", autocomplete=frozenset({"one-time-code"}))

    assert a_sign_in_page(otp) and asks_for_a_code(otp)
