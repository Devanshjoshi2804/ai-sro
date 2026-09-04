"""Take the credentials out of an upload, once, before any of it is stored.

The extension redacts before it sends, and demonstrably does -- the stored
batches are full of `«redacted»` where an `Authorization` header was. But a
rule that runs only in a browser is one a browser can be made not to run, and
the audit measured what that costs: a live JWT and the `&code=` that carried it
reached `s3://sro-artifacts/acme/...` with zero markers on that URL, because
`admit()` screens by host policy and `_ndjson()` serialises, and nothing
between them looked at a value.

**One boundary, not several call sites.** Everything an operator's browser
uploads passes through `IngestObservation.execute`, so this runs there, on the
whole batch, and no future writer of an event field has to remember a rule.

What is deliberately NOT redacted is as much of the point as what is. `itemId`,
`query`, `xtype`, `testId`, `role` and `cssPath` are what locators and workflow
shape keys are built from: redacting one silently changes a workflow's identity
between occurrences, so the same job stops matching itself and the mining run
sees two rare tasks instead of one common one. Only the free-text plane --
what a person could read on the screen -- gets the shape rule, because that is
where a page can render a credential.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.observation.admit import Event
from sro.domain.recording.redaction import redact_body
from sro.domain.recording.sensitivity import (
    REDACTED,
    classify_header,
    is_secret,
    is_secret_field,
    redact_shapes,
    redact_url,
)

_URL_KEYS = ("url", "frame_url", "page_url", "location")
"""Every key on any node of the protocol whose value is a URL.

By name rather than by event kind, because they are the same field wearing
four hats: a page event's `url`, a snapshot's `url`, the `frame_url` a request
was issued from, the `page_url` a gesture happened on and a redirect hop's
`location`. Naming them once is what stops the next kind of event from
arriving with a URL nobody redacts.
"""

_PROSE = ("name", "text", "fieldLabel")
"""The free-text fields of an element fingerprint and its ExtJS component.

`label(el)` in the recorder falls back to `innerText`, so a screen showing a
token puts that token here -- and it reached both the per-gesture prompt and
the umbrella prompt in the rig before this was fixed there.

Only the SHAPE rule runs on these, never the name rule: a `fieldLabel` reading
"Password" is a LABEL, and it is the single most useful thing in the evidence
for telling a model what the operator was doing. Measured over the 926 distinct
URLs and 5,422 events in this store: no label moves.
"""


def redact_events(events: Sequence[Event]) -> tuple[Event, ...]:
    """The same events with every credential-shaped or credential-named value gone.

    Copies rather than mutates: the caller's events came off an HTTP request
    body and the rejection report beside them refers to positions in it.
    """
    return tuple(_event(event) for event in events)


def _event(event: Event) -> Event:
    out = dict(event)
    _urls(out)
    gesture = out.get("gesture")
    if isinstance(gesture, Mapping):
        out["gesture"] = _gesture(gesture)
    request = out.get("request")
    if isinstance(request, Mapping):
        out["request"] = _request(request)
    snapshot = out.get("snapshot")
    if isinstance(snapshot, Mapping):
        # The accessibility tree is 27MB of this deployment's 59MB evidence
        # plane -- every string a page rendered, which is where a key shown on
        # screen would sit. Shapes only, never the name rule: the tree's own
        # vocabulary uses `token` and `tokenList` as CDP AXValue TYPE
        # descriptors, and a name rule would blank 2,573 of them here for no
        # protection at all. Measured across 70,636 real nodes: zero shapes,
        # so this costs nothing today and covers the day a page renders one.
        out["snapshot"] = _shapes_only(snapshot)

    detail = out.get("detail")
    if isinstance(detail, str) and detail:
        # Free text on a page event -- a title, an error, whatever the page
        # said -- so it gets the body rule with no content type to go on. A
        # `?magic_link_token=` landed here in the rig's audit.
        out["detail"] = redact_body(detail, content_type=None)[0]
    return out


def _shapes_only(node: object) -> object:
    """Every string under here through `redact_shapes`, and nothing else.

    Structure is preserved exactly -- a locator is built from this tree, so a
    key or a role that changed would change what a skill can find.
    """
    if isinstance(node, str):
        return redact_shapes(node)
    if isinstance(node, Mapping):
        return {key: _shapes_only(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_shapes_only(value) for value in node]
    return node


def _urls(node: dict[str, object]) -> None:
    for key in _URL_KEYS:
        value = node.get(key)
        if isinstance(value, str) and value:
            node[key] = redact_url(value)


def _gesture(gesture: Mapping[str, object]) -> dict[str, object]:
    out = dict(gesture)
    _urls(out)
    target = out.get("target")
    marked = bool(out.get("secret")) or (isinstance(target, Mapping) and bool(target.get("secret")))
    value = out.get("value")
    if marked:
        # What the operator typed into a password field. Dropped rather than
        # marked: `null` is what the extension already sends for one of these,
        # so the stored shape is the same whether or not the browser obeyed.
        out["value"] = None
    elif isinstance(value, str) and value:
        # Not flagged and still a credential: a token pasted into an ordinary
        # search box is not typed into an `input[type=password]`, so nothing
        # upstream marks it. The shape does.
        out["value"] = redact_shapes(value)
    if isinstance(target, Mapping):
        out["target"] = _element(target)
    return out


def _element(node: Mapping[str, object]) -> dict[str, object]:
    """A `target` or the `component` hanging off it -- the same three fields."""
    out = dict(node)
    for key in _PROSE:
        value = out.get(key)
        if isinstance(value, str) and value:
            out[key] = redact_shapes(value)
    attributes = out.get("attributes")
    if isinstance(attributes, Mapping):
        out["attributes"] = _attributes(attributes)
    component = out.get("component")
    if isinstance(component, Mapping):
        out["component"] = _element(component)
    return out


def _attributes(node: object) -> object:
    """Every DOM attribute of the element the operator touched, by all three rules.

    `attributes` is whatever the page happened to put on the element, so no
    single rule reaches it: `data-auth-token` goes by its NAME,
    `href="/cb?access_token=..."` by the URL rule inside its value, and an
    `X-Acme-Ticket` copied onto a `data-` attribute only by its SHAPE.
    `redact_url` ends in `redact_shapes`, so a string leaf gets the last two
    from one call.

    The field rule and not the header one, deliberately: an attribute named
    `placeholder` whose value is "Password" is a label. The key is kept and the
    value replaced, so a reviewer still sees what was taken out.
    """
    if isinstance(node, Mapping):
        return {
            key: REDACTED if is_secret_field(str(key)) else _attributes(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_attributes(item) for item in node]
    if isinstance(node, str):
        return redact_url(node)
    return node


def _request(request: Mapping[str, object]) -> dict[str, object]:
    out = dict(request)
    _urls(out)
    for key in ("request_headers", "response_headers"):
        headers = out.get(key)
        if isinstance(headers, Mapping):
            out[key] = _headers(headers)
    for key in ("request_body", "response_body"):
        body = out.get(key)
        if isinstance(body, Mapping):
            out[key] = _body(body)
    chain = out.get("redirect_chain")
    if isinstance(chain, list):
        out["redirect_chain"] = [_hop(hop) if isinstance(hop, Mapping) else hop for hop in chain]
    return out


def _headers(headers: Mapping[str, object]) -> dict[str, object]:
    """The name kept and the value replaced, so a reader still sees the call was
    authenticated.

    `is_secret(classify_header(...))` is the same set the extension's
    `isSecretHeader` answers true for -- exact list, then the CSRF and session
    hints, with an HTTP/2 pseudo-header decided first because `:authority`
    contains "auth". A header nobody named a credential can still carry one:
    the 34 `X-Goog-Api-Key` values in this store are matched by nothing but
    their shape.
    """
    return {
        name: REDACTED
        if is_secret(classify_header(str(name)))
        else (redact_shapes(value) if isinstance(value, str) else value)
        for name, value in headers.items()
    }


def _body(body: Mapping[str, object]) -> dict[str, object]:
    out = dict(body)
    text = out.get("text")
    if not isinstance(text, str) or not text:
        return out
    mime = out.get("mime_type")
    cleaned, removed = redact_body(text, content_type=mime if isinstance(mime, str) else None)
    out["text"] = cleaned
    if removed:
        # Beside the names the extension already put there. `redact_body`
        # reports a shape as `«shape: jwt»` rather than as a field name,
        # because "this went because it looked like a JWT" is a different fact
        # from "this went because it was called password".
        already = out.get("redacted_fields")
        existing = list(already) if isinstance(already, list) else []
        out["redacted_fields"] = list(dict.fromkeys([*existing, *removed]))
    return out


def _hop(hop: Mapping[str, object]) -> dict[str, object]:
    """One entry of a redirect chain, whose shape the protocol leaves open.

    The extension sends `[]` today and the Steel path sends url/status/location,
    so this reads by key name rather than by a declared type: a hop was the one
    part of a request nothing validated and nothing redacted, and the rig's
    audit put both a `?code=` URL and an `Authorization` header on disk through
    it.
    """
    out = dict(hop)
    _urls(out)
    for key, value in list(out.items()):
        if "headers" in str(key) and isinstance(value, Mapping):
            out[key] = _headers(value)
    return out
