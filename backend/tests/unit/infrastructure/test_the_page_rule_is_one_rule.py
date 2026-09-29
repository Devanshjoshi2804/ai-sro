"""The Python `page_of` and the JavaScript `page` must agree.

`domain/trigger/arrival.py` says why there are two copies at all: both sides
have to agree on what "the same page" means, the rule is stored here and
evaluated in the browser, and a rule with a copy in two languages drifts on
one of them. It said so and nothing held them together.

What a drift costs is not an error anywhere. A rule whose two spellings differ
by one character is a rule that simply never fires: the operator stands on the
page they made it about, the browser compares its string to the stored one,
they are not equal, and nothing happens -- with no failure to read, because
"no rule matched here" is the ordinary answer on every other page in the world.

The corpus is the awkward one: the deployment's real Keycloak sign-in page
(long host, deep path, a query that must be dropped), a port, a trailing
slash, an uppercase host, a bare host with no path, and the two schemes that
are not a system at all.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

NUDGE = (
    Path(__file__).resolve().parents[3].parent
    / "new-chrome-extension"
    / "src"
    / "panel"
    / "nudge.js"
)

# The rule a browser evaluates is `page()` lowercased -- `rulePage` in
# `service-worker.js` -- because this side stores rules lowercase so the two
# spellings compare as one.
_DRIVER = """
import {{ page }} from "{module}";
const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const said = JSON.parse(chunks.join(""));
process.stdout.write(
  JSON.stringify(
    said.map((url) => {{
      try {{
        if (!/^https?:$/.test(new URL(url).protocol)) return "";
      }} catch {{
        return "";
      }}
      return page(url).toLowerCase();
    }}),
  ),
);
"""

PAGES = (
    # The deployment's own sign-in page, with the whole OAuth query on it.
    "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
    "/auth/realms/bf56-001-eus2/protocol/openid-connect/auth"
    "?client_id=bf56-001-eus2-liam&redirect_uri=https%3a%2f%2fexample&state=abc",
    # And the same page with nothing after it, which is what a rule holds.
    "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
    "/auth/realms/bf56-001-eus2/protocol/openid-connect/auth",
    "https://wms.example/receiving/",
    "https://wms.example/receiving",
    "https://wms.example",
    "https://wms.example/",
    "https://WMS.Example/Receiving",
    "https://wms.example:8443/receiving",
    "https://wms.example/receiving#tab=two",
    "https://wms.example/receiving?facility=BLR1#tab=two",
    # Blue Yonder routes on the fragment: two screens of one `/portal`.
    "https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG"
    "#wm.config/wm.config.partners.customers.types////",
    "https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG"
    "#wm.config/wm.config.equipment.equipment.transportequipmenttype////",
    # An OAuth callback: pairs, and a token with dots in it, never a route.
    "https://wms.example/cb#access_token=eyJhbGci.eyJzdWIi.c2ln&token_type=Bearer",
    # Not a system, on either side.
    "chrome://settings",
    "file:///Users/somebody/page.html",
    "about:blank",
)

SCHEMELESS = "keycloak.example/auth/realms/x/protocol/openid-connect/auth"
"""The one deliberate difference, named here so it stays deliberate.

`page_of` prepends `https://` to anything with no scheme, because this side
also calls it on strings that are ALREADY page-shaped -- a miner's
`starts_on`, a rule read back out of a row. The browser never does: every url
it passes in came from `chrome.tabs` or a navigation event and has a scheme.
So the browser answers "" for a bare host and this side answers the page, and
neither is wrong for what it is given.
"""


def _in_the_browsers_copy(urls: tuple[str, ...]) -> list[str]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed; `make test-extension` needs it too")
    if not NUDGE.is_file():
        pytest.skip(f"the extension's {NUDGE.name} is not in this checkout")
    done = subprocess.run(  # noqa: S603 -- node, found on PATH, on a file in this repo
        [node, "--input-type=module", "-e", _DRIVER.format(module=NUDGE.as_uri())],
        input=json.dumps(list(urls)),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return list(json.loads(done.stdout))


def test_the_two_copies_of_the_page_rule_answer_identically() -> None:
    from sro.domain.trigger.arrival import page_of

    in_the_browser = _in_the_browsers_copy(PAGES)
    for url, theirs in zip(PAGES, in_the_browser, strict=True):
        assert page_of(url) == theirs, (
            f"the two copies of the page rule disagree on {url!r}: "
            f"python gave {page_of(url)!r}, the browser gave {theirs!r} -- "
            "a rule spelled two ways is a rule that never fires"
        )


def test_the_rule_this_deployment_actually_holds_matches_the_page_it_is_about() -> None:
    """The end of the wire, asserted as one string.

    `trg_a925ce7d` fires `Log in to Keycloak` when the operator lands on the
    sign-in page. The stored rule is what the browser compares against, and
    the browser sees the url with the whole OAuth query on it.
    """
    from sro.domain.trigger.arrival import Arrival

    landed = (
        "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
        "/auth/realms/bf56-001-eus2/protocol/openid-connect/auth"
        "?client_id=bf56-001-eus2-liam&redirect_uri=https%3a%2f%2fexample&state=abc"
    )
    rule = Arrival(
        page="keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
        "/auth/realms/bf56-001-eus2/protocol/openid-connect/auth"
    )

    assert rule.matches(landed)
    [theirs] = _in_the_browsers_copy((landed,))
    assert theirs == rule.page


def test_the_one_deliberate_difference_is_a_url_with_no_scheme() -> None:
    """See `SCHEMELESS`. Asserted rather than left implicit, so the day one
    side changes its mind the other hears about it."""
    from sro.domain.trigger.arrival import page_of

    assert page_of(SCHEMELESS) == SCHEMELESS
    assert _in_the_browsers_copy((SCHEMELESS,)) == [""]
