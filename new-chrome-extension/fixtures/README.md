# Golden payloads

Captured from a real session, not written by hand — `make fixtures` drives a
real Chrome with this extension loaded and writes what it actually emitted.
Consumed by `backend/tests/contract/test_observation_payloads.py`.

A hand-written fixture proves the fixture. These exist so that a change on
either side of the frozen contract fails both people's `make check`, and that
only works while they are evidence.

Shapes are specified in [`docs/14-extension-protocol.md`](../../docs/14-extension-protocol.md).

| File | Contains |
|---|---|
| `gesture-click.json` | one `gesture` event, a click on a control |
| `gesture-type.json` | one `gesture` event, text typed into a field |
| `gesture-select.json` | one `gesture` event, a dropdown choice |
| `gesture-press.json` | one `gesture` event, Enter / Escape / Tab |
| `gesture-upload.json` | one `gesture` event, a file chosen |
| `gesture-secret.json` | a credential field — `value` null, `secret` true, and no `value` in `target.attributes` |
| `request-get.json` | one `request` event, a successful read |
| `request-post.json` | one `request` event, a write with a request body and a response body |
| `request-failed.json` | one `request` event that never completed — `failure_reason` set, `status` null |
| `request-with-body.json` | an XHR with a body each way — the other transport, patched separately |
| `request-uninspectable-body.json` | a response nothing read: an event stream stays open for the life of the page |
| `page-navigated.json` | one `page` event |
| `snapshot.json` | one `snapshot` event — an accessibility tree, teaching tier |
| `batch.json` | a complete `POST /v1/observations` body |
| `batch-teaching.json` | a teaching batch, naming the demonstration it belongs to |
| `command-ui-perform-reply.json` | an extension → server reply to `ui.perform` |
| `command-http-send-reply.json` | an extension → server reply to `http.send` |

The test skips itself while this directory holds no `.json` files, so an empty
directory does not block the backend track. Once a file exists it is checked, and
a file that does not parse fails the build.

A second test — `backend/tests/browser/test_the_fixtures_are_still_evidence.py`
— captures a fresh set on every `make check` and compares the *shape* of each
committed file against it: same keys, nested the same way, values ignored
because a port number and a pixel bound differ every run. A file that still
parses but no longer resembles what the extension emits would otherwise pass
the contract test forever, and the two tracks would go on believing they fit.
