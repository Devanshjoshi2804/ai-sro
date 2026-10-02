from sro.domain.observation.gesture import Choice, CookieSeen, Effect, FieldChange, Place, Seen
from sro.domain.observation.seen import (
    K_SEEN_ITEMS,
    choice_from,
    cookies_from,
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
