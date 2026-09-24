"""Spec §5.6: a sign-in page is known by what it holds or by the flow it is in.

Never by its host. A page holding a password or one-time-code field is one;
so is every page a tab passes through between an OAuth/OIDC authorize request
and the navigation that brings it back to the `redirect_uri`'s origin.
"""

from __future__ import annotations

from sro.domain.observation.redaction import redact_url as redact_url_on_ingest
from sro.domain.recording.sensitivity import (
    REDACTED,
    SignInFlow,
    is_sign_in_field,
    redact_url,
)

APP = "https://wms.example"
AUTHORIZE = (
    "https://login.idp.example/common/oauth2/v2.0/authorize?client_id=app"
    "&response_type=code&redirect_uri=https%3A%2F%2Fwms.example%2Fcallback&state=s1&scope=openid"
)


def test_a_password_or_one_time_code_field_makes_a_sign_in_page() -> None:
    assert is_sign_in_field({"type": "password"})
    assert is_sign_in_field({"type": "PASSWORD"})
    assert is_sign_in_field({"autocomplete": "current-password"})
    assert is_sign_in_field({"autocomplete": "section-login new-password"})
    assert is_sign_in_field({"autocomplete": "one-time-code"})


def test_an_ordinary_field_does_not() -> None:
    assert not is_sign_in_field({"type": "tel", "name": "otc", "autocomplete": "off"})
    assert not is_sign_in_field({"type": "text", "autocomplete": "username"})
    assert not is_sign_in_field({})


def test_a_tab_is_inside_the_flow_from_the_authorize_request_to_the_return_with_a_code() -> None:
    flow = SignInFlow()

    assert flow.navigated(f"{APP}/orders") is False
    assert flow.navigated(AUTHORIZE) is True
    assert flow.navigated("https://login.idp.example/common/login") is True
    assert flow.navigated("https://login.idp.example/common/SAS/ProcessAuth") is True
    assert flow.navigated(f"{APP}/callback?code=AUTHCODE&state=s1") is False
    assert flow.navigated(f"{APP}/orders") is False


def test_the_flow_also_ends_when_the_tab_goes_back_to_the_app_without_a_code() -> None:
    flow = SignInFlow()
    flow.navigated(AUTHORIZE)

    assert flow.navigated(f"{APP}/home") is False
    assert flow.navigated("https://login.idp.example/common/login") is False


def test_an_id_token_in_the_fragment_ends_it_too() -> None:
    flow = SignInFlow()
    flow.navigated(AUTHORIZE)

    assert flow.navigated(f"{APP}/callback#id_token=j.w.t&state=s1") is False


def test_a_provider_on_the_apps_own_origin_ends_only_on_the_return_with_a_code() -> None:
    flow = SignInFlow()
    authorize = (
        f"{APP}/authorize?response_type=code&client_id=app&redirect_uri={APP}/callback&state=s1"
    )

    assert flow.navigated(authorize) is True
    assert flow.navigated(f"{APP}/sign-in") is True
    assert flow.navigated(f"{APP}/callback?code=AUTHCODE&state=s1") is False


def test_a_url_missing_one_of_the_four_parameters_starts_nothing() -> None:
    flow = SignInFlow()

    assert flow.navigated(f"{APP}/x?response_type=code&client_id=app&state=s1") is False
    assert (
        flow.navigated(f"{APP}/x?response_type=code&client_id=app&redirect_uri=nowhere&state=s1")
        is False
    )


def test_a_hash_routed_callback_loses_its_code() -> None:
    for redact in (redact_url, redact_url_on_ingest):
        assert (
            redact(f"{APP}/callback#/done?code=FRAGCODE77&state=s1")
            == f"{APP}/callback#/done?code={REDACTED}&state=s1"
        )
        assert redact(f"{APP}/callback#id_token=abc&state=s1") == (
            f"{APP}/callback#id_token={REDACTED}&state=s1"
        )
        assert redact(f"{APP}/#/orders?facility=BLR1") == f"{APP}/#/orders?facility=BLR1"
