import json
import re
from collections.abc import Callable

from rig.correlate import correlate
from rig.records import Gesture
from rig.trim import (
    REDACTED,
    SECRET_HEADER_HINTS,
    SECRET_HEADERS,
    SECRET_WORDS,
    body_keys,
    path_shape,
    thin,
    trim,
)
from rig.wire import (
    SECRET_SHAPES,
    SECRET_SHAPES_ANY_CASE,
    Batch,
    Body,
    Request,
    Target,
    _words_of,
)
from rig.wire import Gesture as WireGesture
from tests.fixtures import BATCH, GESTURE_TYPE, repo_root


def _typed_gesture():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "new")
    return next(g for g in gestures if g.gesture.kind == "type" and not g.gesture.secret)


def test_the_component_chain_survives_because_it_is_what_names_the_control() -> None:
    trimmed = trim(_typed_gesture())

    assert trimmed["target"]["itemId"] == "clientCode"
    assert trimmed["target"]["fieldLabel"] == "Client Code"


def test_a_control_with_no_component_still_trims() -> None:
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "new")
    select = next(g for g in gestures if g.gesture.kind == "select")

    trimmed = trim(select)

    assert trimmed["target"]["itemId"] is None
    assert trimmed["target"]["name"] == "Dock"


def test_cssPath_and_xpath_are_not_sent_to_the_model() -> None:
    """Long, meaningless to a model, and the two locators that break."""
    text = json.dumps(trim(_typed_gesture()))

    assert "cssPath" not in text
    assert "xpath" not in text
    assert "/html/body" not in text


def test_a_json_body_keeps_its_keys() -> None:
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "new")
    with_post = next(g for g in gestures if any(r.method == "POST" for r in g.requests))

    calls = trim(with_post)["calls"]
    posted = next(c for c in calls if c["method"] == "POST")

    assert "clientCode" in posted["body_keys"]


def test_a_form_encoded_body_keeps_its_keys_too() -> None:
    """One of the committed calls is clientCode=ACME-4471&dock=D3."""
    from rig.trim import body_keys
    from rig.wire import Body

    body = Body(
        text="clientCode=ACME-4471&dock=D3",
        mime_type="application/x-www-form-urlencoded",
    )

    assert body_keys(body) == {"clientCode": "ACME-4471", "dock": "D3"}


def test_a_failed_call_with_no_body_does_not_explode() -> None:
    from rig.trim import body_keys

    assert body_keys(None) is None


def test_a_long_value_is_truncated() -> None:
    from rig.trim import VALUE_CHARS, body_keys
    from rig.wire import Body

    body = Body(text=json.dumps({"note": "x" * 500}), mime_type="application/json")

    assert len(body_keys(body)["note"]) <= VALUE_CHARS


def test_a_credential_gesture_carries_no_value() -> None:
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "new")
    secret = next(g for g in gestures if g.gesture.secret)

    assert trim(secret)["value"] is None


def test_a_target_with_a_label_is_not_thin() -> None:
    assert thin(Target.model_validate(GESTURE_TYPE["gesture"]["target"])) is False


def test_a_target_with_only_a_css_path_is_thin() -> None:
    bare = Target.model_validate({"tag": "div", "cssPath": "div > div:nth-child(3)"})

    assert thin(bare) is True


def test_an_id_in_a_path_becomes_a_star() -> None:
    assert path_shape("https://x/data/WM/wm/addresses/1183") == "/data/WM/wm/addresses/*"
    assert path_shape("https://x/api/orders") == "/api/orders"


def test_an_ordinary_hyphenated_route_survives() -> None:
    """The rule this replaced starred any long hyphenated segment, erasing the
    route information that says what the operator actually did."""
    assert path_shape("https://x/api/client-code-detail") == "/api/client-code-detail"
    assert path_shape("https://x/api/order-status") == "/api/order-status"


def test_a_segment_that_is_mostly_digits_is_an_id() -> None:
    assert path_shape("https://x/api/sku-123456") == "/api/*"
    assert path_shape("https://x/api/product-8834726591") == "/api/*"


def test_a_uuid_is_an_id() -> None:
    """A UUID is fine to keep starred, but it does not discriminate the fix:
    a 36-char hyphenated UUID satisfies the *old* `len > 12 and "-" in part`
    rule too, so this assertion alone passed before the fix and after it.
    No UUID can discriminate the two rules -- one always has both a hyphen
    and length > 12, so it always satisfies the old rule as well. Assert the
    new rule's actual boundary instead: len >= 8 with at least half digits.
    """
    assert path_shape("https://x/v1/f47ac10b-58cc-4372-a567-0e02b2c3d479/edit") == "/v1/*/edit"

    # len == 8, digits == 4 (exactly half): the boundary the old rule can't
    # see at all -- no hyphen, so old_rule("ab12cd34") is False.
    assert path_shape("https://x/api/ab12cd34") == "/api/*"
    # len == 8, digits == 3 (just under half): stays a route segment.
    assert path_shape("https://x/api/abc123de") == "/api/abc123de"
    # len == 7 with enough digits: too short to qualify on digit density alone.
    assert path_shape("https://x/api/ab1234c") == "/api/ab1234c"


def test_a_targetless_scroll_trims_and_thins_without_a_crash() -> None:
    """The committed batch has no scroll, and correlate() only ever produces
    a Gesture from a parsed event -- so this builds the records.Gesture
    directly, the way correlate() itself does, rather than going through it."""
    scroll = Gesture(
        id="ges_scroll",
        tenant="new",
        stream_id="dev_test",
        batch_id="bat_test",
        at=1.0,
        url="https://wms.example/portal/page",
        system="https://wms.example",
        tab_id=8,
        frame_url="https://wms.example/portal/page",
        gesture=WireGesture(kind="scroll", value="0", at=1.0),
    )

    assert thin(scroll.gesture.target) is True

    trimmed = trim(scroll)

    assert trimmed["target"]["role"] is None
    assert trimmed["target"]["name"] is None
    assert trimmed["target"]["text"] is None
    assert trimmed["target"]["testId"] is None
    assert trimmed["target"]["itemId"] is None
    assert trimmed["target"]["fieldLabel"] is None
    assert trimmed["target"]["xtype"] is None
    assert trimmed["target"]["query"] is None


def test_a_credential_cannot_be_reached_by_mutating_the_target() -> None:
    """trim() holds this itself rather than inheriting it from wire.Gesture,
    whose validator does not re-run when a nested Target is mutated."""
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "new")
    ordinary = next(g for g in gestures if g.gesture.kind == "type" and not g.gesture.secret)

    ordinary.gesture.target.secret = True

    assert trim(ordinary)["value"] is None


def test_a_password_in_a_request_body_never_reaches_the_prompt() -> None:
    """A click on a Login button is not a secret gesture, so every guard that
    keys on is_secret(gesture) stands aside, and the model was shown the
    password. This asserts the prompt half only; the store half it used to
    claim is asserted -- on disk, WAL included -- by
    test_api.test_a_credential_value_is_nowhere_on_disk."""
    from rig.trim import REDACTED, body_keys
    from rig.wire import Body

    keys = body_keys(
        Body(mime_type="application/json", text='{"user": "amy", "password": "hunter2"}')
    )

    assert keys == {"user": "amy", "password": REDACTED}


def test_a_field_is_secret_by_its_words_and_not_by_its_letters() -> None:
    """Substring matching flags a real field in this tenant's captured data."""
    from rig.trim import is_secret_name

    assert is_secret_name("password")
    assert is_secret_name("apiKey")
    assert is_secret_name("api_key")
    assert is_secret_name("X-Auth-Token")
    assert not is_secret_name("Shipping Date Escalation")
    assert not is_secret_name("username")
    assert not is_secret_name("")


def _extension_source() -> str:
    source = repo_root() / "new-chrome-extension/src/content/sensitivity.module.js"
    return source.read_text(encoding="utf-8")


def _declared_in_the_extension(name: str) -> str:
    """The literal inside the extension's `const <name> = ...` declaration."""
    listed = re.search(rf"const {name} = (?:new Set\()?\[(.*?)\]", _extension_source(), re.DOTALL)
    assert listed, f"the extension's {name} declaration moved"
    return listed.group(1)


def _words(literal: str) -> set[str]:
    return {word.strip().strip("\"'") for word in literal.split(",") if word.strip()}


def test_the_copied_secret_words_still_match_the_extension() -> None:
    """SECRET_WORDS is hand-copied from the extension, whose own copy is
    generated. Nothing else checks the two agree, and a rule that silently
    stops matching what the browser matches is worse than no rule.

    What this and its three neighbours guarantee, precisely: the two
    VOCABULARIES agree -- words, headers, header hints, and the marker -- and,
    below, that the two word SPLITTERS agree. What no test here guarantees is
    that the two sides do the same thing with those words. The rig deliberately
    does one thing the browser does not: `_redact_query` has an OAuth rule that
    blanks a bare `code` parameter beside another OAuth parameter, and the
    extension has no such rule. That divergence is intended. A second,
    accidental one in `redact_url`, `redact_body` or the header rule would not
    be caught by anything in this file.
    """
    assert _words(_declared_in_the_extension("SECRET_WORDS")) == SECRET_WORDS


def _splitter_declared_in_the_extension() -> Callable[[str], list[str]]:
    """The extension's `wordsOf`, rebuilt from its own source as a Python
    function. Its two substitutions and its split are written in a syntax both
    engines read the same way, so this is the rule itself rather than a
    paraphrase of it -- and it fails if the extension gains, loses or reorders
    a substitution."""
    body = re.search(r"const wordsOf = \(text\) =>(.*?);\n", _extension_source(), re.DOTALL)
    assert body, "the extension's wordsOf declaration moved"
    steps = re.findall(r"\.replace\(/(.+?)/g, '(.*?)'\)", body.group(1))
    assert steps, "the extension's wordsOf has no substitutions left"
    split_on = re.search(r"\.split\(/(.+?)/\)", body.group(1))
    assert split_on, "the extension's wordsOf no longer splits"

    def words_of(text: str) -> list[str]:
        spaced = text or ""
        for pattern, replacement in steps:
            spaced = re.sub(pattern, replacement.replace("$", "\\"), spaced)
        return [word.lower() for word in re.split(split_on.group(1), spaced) if word]

    return words_of


def test_the_copied_word_splitter_still_matches_the_extension() -> None:
    """The vocabulary test above compares words; this compares the rule that
    finds them. `saml` was in both lists and caught `SAMLResponse` in neither,
    because the splitter -- not the vocabulary -- was the thing that had to
    change, and nothing here would have noticed the two sides disagreeing
    about it."""
    theirs = _splitter_declared_in_the_extension()
    for name in (
        "SAMLResponse",
        "SSOToken",
        "JWTToken",
        "APIKey",
        "pickNPassAutoDropLocation",
        "api_key",
        "apiKey",
        "X-Auth-Token",
        "Shipping Date Escalation",
        "NLSSORTSetting",
        "",
    ):
        assert _words_of(name) == theirs(name), f"the two splitters disagree about {name!r}"


def _shape_declared_in_the_extension(name: str) -> str:
    """The pattern string inside the extension's `const <name> = new RegExp(...)`.

    A JSON string rather than a `/.../` literal on that side, because two of
    these patterns carry a `/` inside a character class and hand-escaping a
    slash is exactly how the two copies stop being the same expression. So
    `json.loads` gives back the pattern itself, byte for byte.
    """
    declared = re.search(rf"const {name} = new RegExp\((\".*?\"), '", _extension_source())
    assert declared, f"the extension's {name} declaration moved"
    return json.loads(declared.group(1))


def _as_javascript(shapes: tuple[tuple[str, str], ...]) -> str:
    """The rig's alternation spelled the way JavaScript spells it.

    One character of difference in the whole rule: `(?P<name>)` in Python is
    `(?<name>)` in JavaScript. Everything either engine could read differently
    -- a class, a quantifier, an escape -- is compared here literally.
    """
    return "|".join(f"(?<{name}>{pattern})" for name, pattern in shapes)


def test_the_copied_secret_shapes_still_match_the_extension() -> None:
    """The shape rule is hand-copied from the generated extension module the
    same way SECRET_WORDS is, and a value rule that silently stops matching
    what the browser matches is worse than no value rule: the browser's copy
    runs first, so the rig's is the one that catches what a browser was made
    not to run."""
    assert _as_javascript(SECRET_SHAPES) == _shape_declared_in_the_extension("SECRET_SHAPE")
    assert _as_javascript(SECRET_SHAPES_ANY_CASE) == _shape_declared_in_the_extension(
        "SECRET_SHAPE_ANY_CASE"
    )


def test_the_case_blind_shapes_are_the_only_case_blind_ones() -> None:
    """`AKIA`, `AIza` and `eyJ` are case-SENSITIVE prefixes, and matching them
    blind widens each one over the lowercase identifiers this traffic is full
    of. The split only holds if both sides put the same patterns in the same
    half, so the flags are checked too."""
    flags = re.findall(
        r"const SECRET_SHAPE\w* = new RegExp\(\".*?\", '(\w+)'\)", _extension_source()
    )
    assert flags == ["g", "gi"], flags
    assert not set(dict(SECRET_SHAPES)) & set(dict(SECRET_SHAPES_ANY_CASE))


def test_the_copied_marker_still_matches_the_extension() -> None:
    """A marker that has drifted is worse than no marker: every reviewer's
    grep for the redaction the browser writes comes back empty."""
    literal = re.search(r"const REDACTED = '([^']*)'", _extension_source())
    assert literal, "the extension's REDACTED declaration moved"
    assert literal.group(1) == REDACTED


def test_the_copied_header_rule_still_matches_the_extension() -> None:
    """Same drift, one boundary further in: these are what wire.Request applies
    to every stored request."""
    assert _words(_declared_in_the_extension("SECRET_HEADERS")) == SECRET_HEADERS
    assert _words(_declared_in_the_extension("SECRET_HEADER_HINTS")) == set(SECRET_HEADER_HINTS)


def test_body_keys_redacts_on_every_way_out_of_it() -> None:
    """Four returns, one of which was guarded. The other three are how a form
    body with no mime type, a SOAP login and a JSON array reached the prompt."""
    bodies = [
        Body(text='{"password": "hunter2"}', mime_type="application/json"),
        Body(text="user=bob&password=hunter2", mime_type="application/x-www-form-urlencoded"),
        Body(text="user=bob&password=hunter2"),  # form shape, no mime type
        Body(text="<Login><password>hunter2</password></Login>", mime_type="text/xml"),
        Body(text='[{"password": "hunter2"}]', mime_type="application/json"),
        Body(text='"password=hunter2"', mime_type="application/json"),
        Body(text='mutation{login(password:"hunter2")}', mime_type="application/graphql"),
    ]

    for body in bodies:
        keys = body_keys(body)

        assert keys is not None
        assert "hunter2" not in json.dumps(keys, ensure_ascii=False), body.text
        assert REDACTED in json.dumps(keys, ensure_ascii=False), body.text


def test_body_keys_recurses_at_every_depth() -> None:
    """`{"auth": {"password": ...}}` walked past the flat rule. Two levels
    here, not one: a rule that descends exactly once looks identical to a
    recursive one on the shallow case and leaks on the real payload."""
    keys = body_keys(
        Body(text='{"request": {"auth": {"password": "hunter2"}}}', mime_type="application/json")
    )

    assert keys == {"request": f"{{'auth': {{'password': '{REDACTED}'}}}}"}


def test_body_keys_still_names_what_it_saw() -> None:
    keys = body_keys(Body(text='{"clientCode": "ACME-4471"}', mime_type="application/json"))

    assert keys == {"clientCode": "ACME-4471"}


def test_a_suppressed_body_is_nothing_to_read_not_a_crash() -> None:
    """`{"text": null, ...}` is the exact shape the extension sends when it
    declines to keep a body, and it arrives with whatever mime type the call
    had. `parse_qsl(None)` raises TypeError, and the json path invents a
    `{"_": ""}` key out of a body that was never there."""
    for body in (
        Body(text=None, mime_type="application/x-www-form-urlencoded"),
        Body(text=None, mime_type="application/json"),
        Body(text=None, mime_type="text/xml"),
        Body(text=None),
        Body(text="", mime_type="application/json"),
    ):
        assert body_keys(body) is None, body


def test_a_body_with_more_keys_than_the_cap_is_cut_to_it() -> None:
    """BODY_KEYS. A WMS grid save posts a row per line; the prompt is not the
    place for four hundred column names."""
    from rig.trim import BODY_KEYS

    body = Body(
        text=json.dumps({f"column{n}": n for n in range(BODY_KEYS * 3)}),
        mime_type="application/json",
    )

    keys = body_keys(body)

    assert keys is not None
    assert len(keys) == BODY_KEYS
    assert list(keys) == [f"column{n}" for n in range(BODY_KEYS)]


def test_a_body_that_is_not_an_object_is_named_rather_than_indexed() -> None:
    """The non-dict guard. A JSON array, a bare string and a GraphQL mutation
    all parse to something with no keys to name -- and `parsed[key]` on a list
    whose entries are dicts is a TypeError, in the one function every request
    body in every prompt passes through."""
    for body in (
        Body(text='[{"clientCode": "ACME-4471"}]', mime_type="application/json"),
        Body(text='"clientCode=ACME-4471"', mime_type="application/json"),
        Body(text="7", mime_type="application/json"),
    ):
        keys = body_keys(body)

        assert keys is not None, body.text
        assert list(keys) == ["_"], body.text


def test_a_suppressed_body_does_not_read_as_an_absent_one() -> None:
    """`None` for both told the model a call carried nothing when the truth was
    that the extension declined to keep what it carried. Its own comment names
    the failure: a suppressed body "reads to a reviewer as a body that was
    checked and found clean"."""
    assert body_keys(None) is None
    assert body_keys(Body(text=None)) is None

    for why in ("«not captured»", "«dropped: larger than the tenant's max_body_bytes»"):
        assert body_keys(Body(text=None, redacted_fields=[why])) == {"_": why}


def test_a_blocked_request_does_not_read_as_one_still_in_flight() -> None:
    """status and failure are both null on a blocked request, which is exactly
    what a request that never came back looks like."""
    from rig.trim import _call

    blocked = _call(
        Request(
            request_id="r1",
            method="GET",
            url="https://wms.example/wm/addresses",
            started_at="2026-08-12T08:21:09.929Z",
            blocked_reason="blocked by the browser's policy",
        )
    )

    assert blocked["status"] is None
    assert blocked["failed"] is None
    assert blocked["blocked"] == "blocked by the browser's policy"
