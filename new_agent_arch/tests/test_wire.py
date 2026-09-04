import json

import pytest
from pydantic import ValidationError

from rig.wire import (
    REDACTED,
    SECRET_HEADER_HINTS,
    UNINSPECTABLE,
    Batch,
    GestureEvent,
    Request,
    RequestEvent,
    is_secret_header,
    parse_batch,
    redact_body,
    redact_url,
)
from tests.fixtures import (
    BATCH,
    GESTURE_SECRET,
    GESTURE_TYPE,
    PAGE_NAVIGATED,
    REQUEST_FAILED,
    REQUEST_POST,
)


def test_the_committed_batch_parses_unchanged() -> None:
    batch = Batch.model_validate(BATCH)

    assert batch.device_id == "dev_browsertest"
    assert batch.mode == "passive"
    assert len(batch.events) == len(BATCH["events"])


def test_a_batch_id_is_not_required_to_be_hex() -> None:
    """The real one is bat_browsertest_418908ee_1."""
    assert Batch.model_validate(BATCH).batch_id.startswith("bat_")


def test_an_extjs_control_keeps_its_component_chain() -> None:
    event = GestureEvent.model_validate(GESTURE_TYPE)

    assert event.gesture.target.component is not None
    assert event.gesture.target.component.itemId == "clientCode"
    assert event.gesture.target.component.query == "panel#clients textfield#clientCode"


def test_a_plain_html_control_has_component_null() -> None:
    """Only ExtJS widgets carry one. It is an explicit null, not an absent key."""
    select = next(
        e for e in BATCH["events"] if e["kind"] == "gesture" and e["gesture"]["kind"] == "select"
    )

    event = GestureEvent.model_validate(select)

    assert event.gesture.target.component is None


def test_a_credential_value_does_not_survive_parsing() -> None:
    """AGENTS.md: credential values never reach storage. This is the boundary."""
    loud = {**GESTURE_SECRET}
    loud["gesture"] = {**GESTURE_SECRET["gesture"], "value": "hunter2"}

    event = GestureEvent.model_validate(loud)

    assert event.gesture.secret is True
    assert event.gesture.value is None
    assert "hunter2" not in event.model_dump_json()


def test_a_scroll_carries_no_target_and_is_still_a_gesture() -> None:
    """Real acme capture: every scroll had the target key absent, and
    requiring it rejected 15% of that sample's gestures."""
    scroll = {
        "kind": "gesture",
        "gesture": {
            "kind": "scroll",
            "value": "0",
            "modifiers": [],
            "at": 1788201874.644,
            "url": "https://wms.example/portal/page",
        },
        "tab_id": 8,
        "frame_url": "https://wms.example/portal/page",
    }

    event = GestureEvent.model_validate(scroll)

    assert event.gesture.target is None
    assert event.gesture.kind == "scroll"


def test_a_request_event_carries_its_own_tab() -> None:
    """A1 relies on this instead of guessing a tab from a host."""
    event = RequestEvent.model_validate(REQUEST_POST)

    assert event.tab_id is not None


def test_a_failed_request_has_no_status_and_no_bodies() -> None:
    event = RequestEvent.model_validate(REQUEST_FAILED)

    assert event.request.status is None
    assert event.request.response_body is None
    assert event.request.failure_reason


def test_a_target_with_no_usable_signal_is_refused() -> None:
    naked = {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "target": {"tag": "div", "component": None},
            "at": 1.0,
            "url": "https://wms.example/",
        },
        "tab_id": 1,
    }

    with pytest.raises(ValidationError):
        GestureEvent.model_validate(naked)


def test_one_unparseable_event_does_not_cost_the_batch() -> None:
    """The protocol: "A rejected event does not reject the batch." """
    raw = json.loads(json.dumps(BATCH))
    good = len(raw["events"])
    raw["events"].append(
        {
            "kind": "gesture",
            "gesture": {
                "kind": "drag",
                "target": {"tag": "div", "cssPath": "div#x"},
                "at": 1.0,
                "url": "https://wms.example/",
            },
            "tab_id": 1,
        }
    )

    batch, rejected = parse_batch(raw)

    assert len(batch.events) == good
    assert len(rejected) == 1
    assert rejected[0].index == good
    assert rejected[0].reason


def test_a_wholly_good_batch_rejects_nothing() -> None:
    batch, rejected = parse_batch(json.loads(json.dumps(BATCH)))

    assert len(batch.events) == len(BATCH["events"])
    assert rejected == ()


def test_a_credential_value_cannot_be_assigned_back_in() -> None:
    """The drop must not depend on every later author remembering."""
    event = GestureEvent.model_validate(GESTURE_SECRET)

    event.gesture.value = "hunter2"

    assert event.gesture.value is None


def test_a_credential_header_never_reaches_the_store() -> None:
    """_call keeps headers out of the prompt; save_batch writes them to the
    store verbatim, which is the half nothing covered."""
    request = Request(
        request_id="req_1",
        method="GET",
        url="https://wms.example/api/orders",
        started_at="2026-09-04T10:00:00Z",
        request_headers={
            "Authorization": "Bearer sk-live-abc",
            "Cookie": "session=abc123",
            "X-Acme-Session-Key": "s3cr3t",
            "Accept": "application/json",
        },
        response_headers={"Set-Cookie": "session=xyz"},
    )

    assert request.request_headers["Authorization"] == REDACTED
    assert request.request_headers["Cookie"] == REDACTED
    assert request.request_headers["X-Acme-Session-Key"] == REDACTED
    assert request.request_headers["Accept"] == "application/json"
    assert request.response_headers["Set-Cookie"] == REDACTED


def test_a_header_is_secret_by_hint_as_well_as_by_name() -> None:
    """Headers match on substring on purpose, unlike body field names: a
    tenant's own `x-acme-session-key` has to match on `sess`."""
    assert is_secret_header("Authorization")
    assert is_secret_header("x-acme-session-key")
    assert is_secret_header("X-XSRF-TOKEN")
    assert not is_secret_header("Accept")
    assert not is_secret_header("Content-Type")
    assert not is_secret_header("")


CLEAN_URL = "https://wms.example/orders?tag=a&tag=b&note=two%20words&q=a+b&empty=#top"


def test_a_url_needing_no_redaction_comes_back_byte_identical() -> None:
    """Not a nicety. Round-tripping through a URL parser collapses the repeated
    `tag`, turns the literal space in `a+b` into something else, re-encodes
    `%20` -- and percent-encodes the marker itself, so grepping stored evidence
    for «redacted» finds nothing. The extension splices by hand for exactly
    this reason and so does this."""
    assert redact_url(CLEAN_URL) == CLEAN_URL


def test_only_the_credential_pair_is_touched() -> None:
    url = f"{CLEAN_URL[:-4]}&session_token=hunter2#top"

    redacted = redact_url(url)

    assert f"session_token={REDACTED}" in redacted
    assert "hunter2" not in redacted
    assert "tag=a&tag=b&note=two%20words&q=a+b" in redacted  # every other byte as it was


def test_a_credential_in_the_fragment_is_replaced() -> None:
    """`#access_token=...` is how an OAuth implicit flow returns a token."""
    redacted = redact_url("https://wms.example/cb#access_token=hunter2&state=abc")

    assert redacted == f"https://wms.example/cb#access_token={REDACTED}&state=abc"


def test_a_relative_or_unparseable_url_is_left_alone() -> None:
    """There is no page here to resolve it against, so it is not guessed at."""
    for url in ("/api/orders?token=x", "not a url at all", ""):
        assert redact_url(url) == url


def test_every_body_shape_the_audit_proved_is_redacted() -> None:
    """Five shapes reached storage and the prompt; one of them was handled."""
    shapes = [
        ('{"password": "hunter2"}', "application/json"),
        ('{"auth": {"login": {"pwd": "hunter2"}}}', "application/json"),  # at depth
        ('[{"password": "hunter2"}]', "application/json"),  # array at the top
        ('"password=hunter2"', "application/json"),  # a bare JSON string
        ("user=bob&password=hunter2", "application/x-www-form-urlencoded"),
        ("user=bob&password=hunter2", None),  # form shape, no mime type
        ("<Login><user>bob</user><password>hunter2</password></Login>", "text/xml"),
        ('<Login user="bob" password="hunter2"/>', None),  # XML attribute form
        ('mutation{login(password:"hunter2")}', "application/graphql"),
        ("user: bob\npassword: hunter2\n", "text/plain"),  # no parser fits
        (
            '--X\r\nContent-Disposition: form-data; name="password"\r\n\r\nhunter2\r\n--X--\r\n',
            'multipart/form-data; boundary="X"',
        ),
    ]

    for text, mime_type in shapes:
        redacted = redact_body(text, mime_type)

        assert redacted is not None
        assert "hunter2" not in redacted, (text, mime_type)
        assert REDACTED in redacted, (text, mime_type)


def test_a_body_that_cannot_be_parsed_is_replaced_whole() -> None:
    """Truncated JSON does not parse, so it cannot be redacted field by field.
    Storing it unexamined is the failure; replacing it is legible and safe."""
    assert redact_body('{"password": "hunter2", "next', "application/json") == UNINSPECTABLE


def test_a_body_with_nothing_secret_in_it_comes_back_byte_identical() -> None:
    """Compact on purpose: a body that merely round-tripped through json.dumps
    would come back with a space after the colon, and every stored body would
    then differ from what the browser sent."""
    assert redact_body('{"clientCode":"ACME-4471"}', "application/json") == (
        '{"clientCode":"ACME-4471"}'
    )


def test_a_redirect_hop_carries_no_credential_to_disk() -> None:
    """redirect_chain was `list[Any]` -- the one field on a Request that
    nothing validated and nothing redacted."""
    request = Request.model_validate(
        {
            "request_id": "r1",
            "method": "GET",
            "url": "https://wms.example/app",
            "started_at": "2026-08-31T08:40:04.765Z",
            "redirect_chain": [
                {
                    "url": "https://sso.example/cb?access_token=hunter2",
                    "status": 302,
                    "location": "https://sso.example/next?api_key=hunter2",
                    "headers": {"Authorization": "Bearer hunter2"},
                }
            ],
        }
    )

    stored = request.model_dump_json()

    assert "hunter2" not in stored
    assert request.redirect_chain[0].status == 302  # the hop itself is still there


def test_an_oauth_code_beside_an_oauth_parameter_is_redacted() -> None:
    """The last row of the audit's proof table: an authorization code on a
    redirect hop. `code` cannot join SECRET_WORDS -- that rule matches whole
    words, and this tenant's capture has 138 distinct field names ending in
    one. So the rule is an exact parameter name plus an OAuth companion."""
    for companion in ("state=xyz", "client_id=abc", "redirect_uri=https%3A%2F%2Fa", "nonce=n1"):
        url = f"https://sso.example/callback?code=hunter2Auth&{companion}"

        assert "hunter2Auth" not in redact_url(url), companion
        assert REDACTED in redact_url(url), companion
        assert companion in redact_url(url), "only the code is touched"


def test_a_warehouse_code_is_not_an_oauth_code() -> None:
    """A false redaction is a real loss of evidence, and the security round
    measured that this direction matters. Nothing here carries an OAuth
    parameter, so nothing here is a credential."""
    untouched = (
        "https://wms.example/api/areas?postalCode=560103",
        "https://wms.example/api/areas?areaCode=A1&operationCode=PICK",
        "https://wms.example/api/orders?code=SO-4471",
        "https://wms.example/api/orders?code=SO-4471&status=OPEN",
        "https://wms.example/api/x?barCodeTemplateId=7&errorCode=E12",
    )
    for url in untouched:
        assert redact_url(url) == url, url


def test_a_request_whose_timestamp_cannot_be_read_is_one_rejected_event() -> None:
    """correlate._epoch parses these strictly and runs after parse_batch, so an
    unparseable started_at used to raise out of the ingest route and cost every
    good event in the batch. The batch boundary owns that decision."""
    raw = json.loads(json.dumps(BATCH))
    bad = json.loads(json.dumps(REQUEST_POST))
    bad["request"]["started_at"] = "2026-09-04 10:00:00 IST"
    raw["events"].append(bad)

    batch, rejected = parse_batch(raw)

    assert len(batch.events) == len(BATCH["events"])
    assert len(rejected) == 1
    assert rejected[0].index == len(BATCH["events"])
    assert "started_at" in rejected[0].reason.split(":", 1)[0]
    assert "IST" in rejected[0].reason


def test_a_page_event_whose_timestamp_cannot_be_read_is_one_rejected_event() -> None:
    raw = json.loads(json.dumps(BATCH))
    bad = json.loads(json.dumps(PAGE_NAVIGATED))
    bad["at"] = "not-a-time"
    raw["events"].append(bad)

    batch, rejected = parse_batch(raw)

    assert len(batch.events) == len(BATCH["events"])
    assert [r.index for r in rejected] == [len(BATCH["events"])]
    assert rejected[0].reason.split(":", 1)[0].endswith(".at")


def test_a_rejected_event_names_the_field_that_could_not_be_read() -> None:
    """ "Input should be a valid number" names nothing anyone can act on."""
    raw = json.loads(json.dumps(BATCH))
    bad = json.loads(json.dumps(GESTURE_TYPE))
    bad["gesture"]["at"] = "not-a-time"
    raw["events"].append(bad)

    _, rejected = parse_batch(raw)

    assert len(rejected) == 1
    assert rejected[0].reason.split(":", 1)[0].endswith(".at")


def test_a_header_only_the_exact_list_names_is_still_a_credential() -> None:
    """SECRET_HEADER_HINTS alone matches every header the rest of the suite
    exercises, so the exact list was dead relative to the tests -- and 2 of the
    3 real header matches in the captured store are hint-only, which is what
    makes an untested exact list a gap rather than dead code. These three carry
    no hint substring at all; the list is the only thing that catches them."""
    for name in ("api-key", "x-api-key", "x-requested-with"):
        assert not any(hint in name for hint in SECRET_HEADER_HINTS), name
        assert is_secret_header(name), name
        assert is_secret_header(name.upper()), name

    assert not is_secret_header("x-request-id")
    assert not is_secret_header("content-type")
