"""The Python `redact_url` and the JavaScript `redactUrl` must agree.

The brief asked whether the rule could be *declared once* and the JavaScript
emitted from it, the way `SECRET_TOKENS` and `SECRET_SHAPES` already are. It
cannot, and the reason is worth writing down rather than discovering again:
what the generator shares today is DATA -- a word list and two regex sources,
`json.dumps`ed into the emitted file, so there is literally one copy of each.
`redact_url` is an ALGORITHM: find the hash, splice the query by raw string
position, decide each pair by its decoded name, then substitute shapes over the
whole thing. Emitting that from the Python would mean a Python-to-JavaScript
translator in this repository, which is a great deal more code -- and more
places to be wrong -- than the thirty lines it would deduplicate.

So there are two implementations, and this is the test that stops them drifting
the way the three word-splitters did. It runs the generated
`sensitivity.module.js` -- the artefact the service worker actually loads, kept
equal to its generator by `test_generated_scripts_are_current.py` -- under node
against the same URLs the Python sees, and demands the same bytes out.

The corpus is deliberately the awkward one: repeated keys, a literal `+`, a
`%20`, an encoded parameter name, a bare anchor, a token in a path segment, a
fragment shaped like a query, and the two real URL shapes from the batch that
put a credential in the blob store.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from sro.infrastructure.steel.generate_extension_recorder import SENSITIVITY_MODULE_OUT

FAKE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJub2JvZHkifQ.not-a-signature"

ABSOLUTE = (
    # Nothing to redact, and every awkward encoding there is.
    "https://wms.example/app?tag=a&tag=b&q=a+b&note=two%20words#view=picking",
    "https://wms.example/docs#section-heading",
    "https://wms.example/docs?q=pick#section-heading",
    "https://wms.example/docs#",
    "https://wms.example/portal",
    # Real shapes, from the batch this change was measured against.
    "https://wms.example/data/MCS/rpux/currencies?siteId=SG&subsites=----&subsites=NEWTEST1",
    f"https://wms.example/portal?state=10831057103308876786&code={FAKE_JWT}",
    "https://wms.example/auth/realms/x/login-actions/authenticate?session_code=Nz3Xq7&tab_id=50_a",
    # Names, in both cases and both encodings.
    "https://wms.example/app?facility=BLR%201&api_key=k",
    "https://wms.example/app?api%5Fkey=k&note=two%20words",
    "https://wms.example/app?jsessionid=A1B2&facility=BLR1",
    "https://wms.example/app?session_id=A1B2&facility=BLR1",
    "https://wms.example/app?token&facility=BLR1",
    "https://wms.example/app?PASSWORD=x&Verification+Code=1234",
    # Fragments, which is how an implicit flow hands a token back.
    "https://wms.example/callback#access_token=ya29.abc&token_type=bearer",
    "https://wms.example/app?facility=BLR%201&api_key=k#id_token=j.w.t&v=1",
    # Shapes, where no parameter name exists to judge the value by.
    f"https://wms.example/reset/{FAKE_JWT}?facility=BLR1",
    "https://wms.example/app?k=AKIAIOSFODNN7EXAMPLE",
    "https://wms.example/app?q=AIzaSyA1234567890123456789012345678901234",
)

RELATIVE = (
    "/v1/orders?api_key=k",
    "/v1/orders#access_token=x",
    "/v1/orders?facility=BLR1",
)

_DRIVER = """
import {{ redactUrl }} from "{module}";
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
process.stdout.write(JSON.stringify(JSON.parse(chunks.join("")).map(redactUrl)));
"""


def _in_the_browsers_copy(urls: tuple[str, ...]) -> list[str]:
    """The generated module, run by node, answering the same list.

    Inline rather than through a driver file, so nothing is written into the
    extension's source tree to run a test.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; `make test-extension` needs it too")
    if not SENSITIVITY_MODULE_OUT.is_file():
        pytest.skip("sensitivity.module.js has not been generated in this checkout")
    done = subprocess.run(  # noqa: S603 -- node, found on PATH, on a generated file in this repo
        [node, "--input-type=module", "-e", _DRIVER.format(module=SENSITIVITY_MODULE_OUT.as_uri())],
        input=json.dumps(list(urls)),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return list(json.loads(done.stdout))


def test_the_two_copies_of_the_url_rule_answer_identically() -> None:
    from sro.domain.recording.sensitivity import redact_url

    in_the_browser = _in_the_browsers_copy(ABSOLUTE)
    for url, theirs in zip(ABSOLUTE, in_the_browser, strict=True):
        assert redact_url(url) == theirs, (
            f"the two copies of the URL rule disagree on {url!r}: "
            f"python gave {redact_url(url)!r}, the browser gave {theirs!r}"
        )


def test_the_one_deliberate_difference_is_the_relative_url_and_only_that() -> None:
    """Named here so it stays deliberate.

    The extension leaves a relative URL alone because a service worker has no
    page to RESOLVE it against. Nothing in the Python resolves anything -- the
    query and fragment are spliced by raw string position -- and the rig
    measured what copying the guard costs: every one of the 611 distinct URLs
    in its captured knowledge base is relative, so a guard meant to be careful
    excluded 100% of real evidence. This backend's own store is the other way
    round (all 926 distinct URLs are absolute), which is exactly why the
    divergence has to be asserted rather than assumed away.
    """
    from sro.domain.recording.sensitivity import REDACTED, redact_url

    in_the_browser = _in_the_browsers_copy(RELATIVE)
    assert in_the_browser == list(RELATIVE), "the browser's copy started redacting relative URLs"
    assert redact_url("/v1/orders?api_key=k") == f"/v1/orders?api_key={REDACTED}"
    assert redact_url("/v1/orders#access_token=x") == f"/v1/orders#access_token={REDACTED}"
    assert redact_url("/v1/orders?facility=BLR1") == "/v1/orders?facility=BLR1"
