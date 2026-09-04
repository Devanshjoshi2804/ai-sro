"""A URL is stored on every event there is, and nothing in Python redacted one.

`redactUrl` existed only as JavaScript, emitted by `generate_extension_recorder`,
so a URL that reached the backend without passing through a content script --
or through a browser that simply did not run the rule -- was written to the
evidence plane exactly as it arrived. It was: a `&code=<jwt>` sits in
`s3://sro-artifacts/acme/...` today.

The behaviour asserted here is the shipped JavaScript's, on purpose. The one
deliberate difference -- a relative URL -- has its own test at the bottom, and
`test_the_url_rule_is_one_rule.py` re-runs the generated JS against this Python
so the two cannot drift silently.
"""

from __future__ import annotations

from sro.domain.recording.sensitivity import REDACTED, redact_url

# A JWT nobody would write down: real base64url header and payload, so the shape
# is genuine, and the word `not-a-signature` where the signature goes. The same
# constant the extension's own test uses.
FAKE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJub2JvZHkifQ.not-a-signature"


def test_a_url_carrying_no_credential_comes_back_byte_identical() -> None:
    """The property the hand-splicing exists to keep.

    Round-tripping through `parse_qsl` + `urlencode` collapses the repeated
    `tag`, turns the literal space in `q=a b` into `+`, re-encodes `%20`, and
    -- when something does match -- percent-encodes the marker itself, so a
    reviewer grepping the evidence store for the «redacted» every other
    redaction path writes finds nothing on a URL.
    """
    for url in (
        "https://wms.example/app?tag=a&tag=b&q=a+b&note=two%20words#view=picking",
        "https://wms.example/docs#section-heading",
        "https://wms.example/data/MCS/rpux/currencies?siteId=SG&subsites=----&subsites=NEWTEST1",
        "https://wms.example/portal",
        "",
    ):
        assert redact_url(url) == url, url


def test_a_credential_named_parameter_loses_its_value_and_keeps_its_bytes() -> None:
    assert redact_url("https://wms.example/app?facility=BLR%201&api_key=k") == (
        f"https://wms.example/app?facility=BLR%201&api_key={REDACTED}"
    )
    # A Java servlet session is one word, matched whole; `session_id` matches
    # through the joined form.
    assert redact_url("https://wms.example/app?jsessionid=A1B2&facility=BLR1") == (
        f"https://wms.example/app?jsessionid={REDACTED}&facility=BLR1"
    )
    assert redact_url("https://wms.example/app?session_id=A1B2&facility=BLR1") == (
        f"https://wms.example/app?session_id={REDACTED}&facility=BLR1"
    )


def test_the_fragment_is_judged_by_the_same_rule_as_the_query() -> None:
    """`#access_token=...` is exactly how an OAuth implicit flow returns a token."""
    assert redact_url("https://wms.example/callback#access_token=ya29.abc&token_type=bearer") == (
        f"https://wms.example/callback#access_token={REDACTED}&token_type={REDACTED}"
    )
    assert redact_url("https://wms.example/app?facility=BLR%201&api_key=k#id_token=j.w.t&v=1") == (
        f"https://wms.example/app?facility=BLR%201&api_key={REDACTED}#id_token={REDACTED}&v=1"
    )


def test_a_bare_anchor_is_not_split_into_pairs_it_never_had() -> None:
    for url in (
        "https://wms.example/docs#section-heading",
        "https://wms.example/docs?q=pick#section-heading",
        "https://wms.example/docs#",
    ):
        assert redact_url(url) == url, url


def test_a_credential_in_a_path_segment_has_no_name_to_be_judged_by() -> None:
    """Which is why the shape pass runs over the whole URL and not the query."""
    assert redact_url(f"https://wms.example/reset/{FAKE_JWT}?facility=BLR1") == (
        f"https://wms.example/reset/{REDACTED}?facility=BLR1"
    )


def test_the_oauth_callback_that_is_sitting_in_the_blob_store_loses_its_code() -> None:
    """The exact shape of the URL this whole change was measured against."""
    landed = redact_url(f"https://wms.example/portal?state=10831057103308876786&code={FAKE_JWT}")
    assert landed == f"https://wms.example/portal?state=10831057103308876786&code={REDACTED}"
    assert "eyJ" not in landed


def test_a_relative_url_is_redacted_too() -> None:
    """The one deliberate difference from the JavaScript, and why.

    The extension leaves a relative URL alone because it cannot RESOLVE one --
    a service worker has no page to resolve against. That reasoning is about
    resolution, and nothing here resolves anything: the query and fragment are
    spliced by raw string position and need no scheme or host. The rig measured
    the cost of copying the guard anyway -- all 611 distinct URLs in its
    captured knowledge base are relative, so a guard meant to be careful
    excluded 100% of real evidence from URL redaction.
    """
    assert redact_url("/v1/orders?api_key=k") == f"/v1/orders?api_key={REDACTED}"
    assert redact_url("/v1/orders#access_token=x") == f"/v1/orders#access_token={REDACTED}"
    # And still byte-identical when there is nothing in it.
    assert redact_url("/v1/orders?facility=BLR1") == "/v1/orders?facility=BLR1"


def test_a_parameter_with_no_value_is_still_named_by_something() -> None:
    """`?token` alone: the name is what matched, and there is no value to keep."""
    assert redact_url("https://wms.example/app?token&facility=BLR1") == (
        f"https://wms.example/app?token={REDACTED}&facility=BLR1"
    )


def test_a_percent_encoded_parameter_name_names_the_same_credential() -> None:
    """`api%5Fkey` is `api_key`. Judged decoded, written back raw, so the pairs
    that did not match keep the encoding the browser sent."""
    assert redact_url("https://wms.example/app?api%5Fkey=k&note=two%20words") == (
        f"https://wms.example/app?api%5Fkey={REDACTED}&note=two%20words"
    )


# A five-segment JWE, which is what an ENCRYPTED token looks like in compact
# serialisation and what the real Okta authorization code in this deployment's
# evidence store actually is: header, encrypted key, iv, ciphertext, tag.
# `FAKE_JWT` above has three segments, so every assertion written against it
# passed while a three-segment rule left two segments of this one on disk.
FAKE_JWE = (
    "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0"
    ".QUVTLXdyYXBwZWQta2V5LXRoYXQtaXMtbm90LXJlYWw"
    ".aXYtMTItYnl0ZXMtMA"
    ".Y2lwaGVydGV4dC13aGljaC1pcy1ub3QtYS1yZWFsLXRva2VuLWF0LWFsbC1ub3BlLW5vdGhpbmc"
    ".dGFnLW5vdC1yZWFs"
)


def test_the_encrypted_token_loses_every_segment_and_not_the_first_three() -> None:
    """The shape actually in the blob store, which the three-segment rule missed.

    A rule that matched `header.key.iv` replaced those and left `.ciphertext.tag`
    sitting beside the marker -- 1,059 characters, in fourteen stored objects.
    That is worse than no match: `«redacted»` is exactly what a reader greps for
    to decide the plane is clean, so a partial redaction reports success.
    """
    landed = redact_url(f"https://wms.example/portal?state=1083105710&code={FAKE_JWE}")
    assert landed == f"https://wms.example/portal?state=1083105710&code={REDACTED}"
    # The tail is the specific failure: assert on the marker's neighbour, not
    # on the `eyJ` prefix the rule itself removes.
    assert "ciphertext" not in landed
    assert f"{REDACTED}." not in landed


def test_an_opaque_authorization_code_is_redacted_beside_an_oauth_companion() -> None:
    """The common case, which had no rule at all on this side.

    The `&code=` in this store was caught only because Okta happens to emit a
    token starting `eyJ` -- the JWT SHAPE matched it. Most providers hand back
    an opaque string with no shape to match, and the name rule cannot help:
    `code` is deliberately absent from SECRET_TOKENS because this tenant's
    traffic carries 138 field names ending in one.
    """
    landed = redact_url(
        "https://wms.example/portal?state=1083105710&code=Xy7_bQ9zAbcDEF-0123456789abcdefGHIJ"
    )
    assert landed == f"https://wms.example/portal?state=1083105710&code={REDACTED}"


def test_a_warehouse_code_with_no_oauth_beside_it_is_left_alone() -> None:
    """The other half of the same rule, and the reason it is narrowed twice.

    `code` as a bare word is a warehouse concept before it is an OAuth one.
    Redacting every parameter named `code` would blank real evidence, so the
    rule needs a companion parameter -- the thing that says this is a callback
    hop rather than an ordinary call.
    """
    untouched = "https://wms.example/api/areas?operationCode=PICK&code=A12&areaCode=DOCK7"
    assert redact_url(untouched) == untouched
