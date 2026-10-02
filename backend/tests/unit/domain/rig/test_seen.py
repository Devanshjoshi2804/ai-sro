import pytest

from sro.domain.observation.gesture import Choice, CookieSeen, Effect, FieldChange, Place, Seen
from sro.domain.observation.outline import _said, said_text
from sro.domain.observation.seen import (
    K_CHOICE_OPTIONS,
    K_SEEN_ITEMS,
    choice_from,
    choice_kept,
    cookies_from,
    cookies_kept,
    effect_from,
    effect_kept,
    extras_kept,
    mail_thread_kept,
    place_from,
    place_kept,
)


def test_a_place_keeps_what_a_person_reads_and_shapes_the_route() -> None:
    raw = {
        "route": "/wms/customers/12345#!/edit/987654321",
        "title": "Customer Types",
        "headings": ["Customer Types", "Edit", "Details", "More"],
        "tabs": ["General"],
        "grid": "Customer Types",
        "landmarks": ["New Customer Type"],
        "version": "Ext 7.6.0",
    }
    assert place_from(raw) == Place(
        route="/wms/customers/*#!/edit/*",
        title="Customer Types",
        headings=("Customer Types", "Edit", "Details"),
        tabs=("General",),
        grid="Customer Types",
        landmarks=("New Customer Type",),
        version="Ext 7.6.0",
    )


def test_a_place_with_nothing_said_is_no_place() -> None:
    assert place_kept({"route": None, "headings": []}) is None
    assert place_kept("not a mapping") is None


def test_effect_text_shaped_like_a_token_is_dropped() -> None:
    kept = effect_kept(
        {
            "appeared": [
                {"role": "status", "text": "Session 3f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c expired"},
                {"role": "status", "text": "Customer type ABC saved"},
                {"role": "alert", "text": "see https://idp.example/login?code=xyz"},
            ]
        }
    )
    assert kept is not None
    assert kept["appeared"] == [
        {"role": "status", "text": "Customer type ABC saved", "title": None, "buttons": []}
    ]


def test_an_effect_keeps_roles_changes_and_timings_and_nothing_else() -> None:
    effect = effect_from(
        {
            "appeared": [
                {
                    "role": "dialog",
                    "title": "Delete?",
                    "text": "Delete this row?",
                    "buttons": ["Yes", "No"],
                },
                {"role": "banner", "text": "not a role we keep"},
            ],
            "vanished": [{"role": "mask"}],
            "route_before": "/a/1",
            "route_after": "/a/2",
            "fields": [
                {"label": "Code", "change": "invalid"},
                {"label": "Code", "change": "exploded"},
            ],
            "requests_ms": 830,
            "mask_ms": 1200.7,
            "quiet_ms": 999999,
            "ended": "quiet",
            "errors": ["TypeError: x is undefined at https://wms.example/app.js:1:2"],
            "shortcuts": ["ctrl+s", "ctrl+password"],
            "value": "anything typed",
        }
    )
    assert effect == Effect(
        appeared=(Seen("dialog", "Delete this row?", "Delete?", ("Yes", "No")),),
        vanished=(Seen("mask"),),
        route_before="/a/*",
        route_after="/a/*",
        fields=(FieldChange("Code", "invalid"),),
        requests_ms=830,
        mask_ms=1200,
        quiet_ms=60_000,
        ended="quiet",
        errors=("TypeError: x is undefined at «url»",),
        shortcuts=("ctrl+s",),
    )


def test_an_effect_is_capped() -> None:
    kept = effect_kept({"appeared": [{"role": "row", "text": f"row {n}"} for n in range(500)]})
    assert kept is not None and len(kept["appeared"]) == K_SEEN_ITEMS


def test_a_choice_keeps_option_labels_and_the_chosen_index() -> None:
    assert choice_from(
        {"chosen": "Retail", "index": 2, "options": ["Bulk", "Pallet", "Retail"]}
    ) == Choice("Retail", 2, ("Bulk", "Pallet", "Retail"))
    assert choice_from({"index": "two"}) is None


def test_a_cookie_is_its_name_and_expiry_never_a_value() -> None:
    assert cookies_from(
        [
            {
                "name": "JSESSIONID",
                "expires_at": 1_790_000_000.5,
                "domain": "wms.example",
                "session": False,
                "value": "abc",
            },
            {"name": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig", "expires_at": None},
            {"name": "x" * 200},
        ]
    ) == (CookieSeen("JSESSIONID", 1_790_000_000.5, "wms.example", False),)


def test_a_mail_thread_reference_is_an_id_or_nothing() -> None:
    assert (
        mail_thread_kept("FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk") == "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"
    )
    assert mail_thread_kept("Re: your order 42") is None
    assert mail_thread_kept("a" * 300) is None


def test_target_extras_pass_the_said_rule() -> None:
    assert extras_kept(
        {
            "labelText": "Customer code *",
            "fullName": "Bearer abcdefghijklmnopqrstuvwxyz0123456789",
            "siblingIndex": 3,
            "siblingCount": "x",
        }
    ) == {"labelText": "Customer code *", "fullName": None, "siblingIndex": 3, "siblingCount": None}


@pytest.mark.parametrize(
    "route",
    [
        "/app#access_token=eyJhbGciOiJIUzI1NiJ9abcdef",
        "/a#access_token=abc123&state=x",
        "/a#=x",
        "/users/john.doe@acme.com/edit",
        "/x/eyJhbGciOiJIUzI1NiJ9.sig/y",
    ],
)
def test_a_route_with_a_secret_in_it_is_no_route(route: str) -> None:
    assert place_kept({"title": "T", "route": route}) == {
        "route": None,
        "title": "T",
        "headings": [],
        "tabs": [],
        "grid": None,
        "landmarks": [],
        "version": None,
    }
    effect = effect_kept({"route_before": route, "route_after": "/ok/1"})
    assert effect is not None and effect["route_before"] is None


def test_a_route_is_capped() -> None:
    kept = place_kept({"route": "/" + "a b/" * 100})
    assert kept is None or len(str(kept["route"])) <= 120


@pytest.mark.parametrize(
    "name",
    [
        "0123456789abcdef0123456789abcdef",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345",
        "sk_live_abcdefgh",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    ],
)
def test_a_cookie_named_like_a_secret_is_dropped(name: str) -> None:
    assert cookies_kept([{"name": name}]) == []


@pytest.mark.parametrize("domain", ["evil\u202e.com?token=abc", "a b.com", "x@y.com", "a/b"])
def test_a_cookie_domain_is_a_hostname_or_nothing(domain: str) -> None:
    (one,) = cookies_kept([{"name": "JSESSIONID", "domain": domain}])
    assert one["domain"] is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 1e300, -5.0])
def test_a_cookie_expiry_is_a_sane_number_or_nothing(bad: float) -> None:
    (one,) = cookies_kept([{"name": "JSESSIONID", "expires_at": bad}])
    assert one["expires_at"] is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_a_timing_that_is_not_a_number_is_no_timing(bad: float) -> None:
    assert effect_kept({"requests_ms": bad, "mask_ms": bad}) is None


@pytest.mark.parametrize(
    "ref",
    [
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig",
        "hunter2",
        "Invoice.42",
    ],
)
def test_a_mail_thread_that_is_not_an_id_is_dropped(ref: str) -> None:
    assert mail_thread_kept(ref) is None


def test_a_mail_hex_id_is_kept() -> None:
    assert mail_thread_kept("18f3a9c2b7d4e601") == "18f3a9c2b7d4e601"


@pytest.mark.parametrize(
    "text",
    [
        "Saved for john.doe@acme.com",
        "call 4111 1111 1111 1111",
        "ref 123456",
        "Password: hunter2",
        "token=abc",
        "secret is hunter2",
        "dGhpcyBpcyBhIHRlc3Qgb2Y",
    ],
)
def test_said_text_drops_personal_text(text: str) -> None:
    assert said_text(text) is None


def test_said_text_strips_control_characters_and_keeps_the_words() -> None:
    assert said_text("Saved\x00\x07") == "Saved"
    assert said_text("a\u202eb") == "ab"
    assert said_text("a\u200bb") == "ab"
    assert said_text("Password reset") == "Password reset"
    assert said_text("Customer Types") == "Customer Types"


def test_a_choice_index_is_bounded() -> None:
    assert choice_kept({"chosen": "A", "index": 10**30}) is None
    assert choice_kept({"chosen": "A", "index": K_CHOICE_OPTIONS - 1}) is not None


def test_the_existing_outline_rule_is_unchanged() -> None:
    assert {
        raw: _said(raw)
        for raw in (
            "Saved\x00\x07",
            "Saved for john.doe@acme.com",
            "Password: hunter2",
            "call 4111 1111 1111 1111",
            "  Customer   types ",
            "a\u202eb",
            "dGhpcyBpcyBhIHRlc3Qgb2Y",
            "x" * 130,
            "id=5",
        )
    } == {
        "Saved\x00\x07": "Saved\x00\x07",
        "Saved for john.doe@acme.com": "Saved for john.doe@acme.com",
        "Password: hunter2": "Password: hunter2",
        "call 4111 1111 1111 1111": "call 4111 1111 1111 1111",
        "  Customer   types ": "Customer types",
        "a\u202eb": "a\u202eb",
        "dGhpcyBpcyBhIHRlc3Qgb2Y": "dGhpcyBpcyBhIHRlc3Qgb2Y",
        "x" * 130: None,
        "id=5": None,
    }
