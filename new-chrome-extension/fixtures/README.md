# Golden payloads

Captured from a real session, not written by hand. Consumed by
`backend/tests/contract/test_observation_payloads.py`.

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
| `page-navigated.json` | one `page` event |
| `snapshot.json` | one `snapshot` event (teaching tier, `Accessibility.getFullAXTree`) |
| `batch.json` | a complete `POST /v1/observations` body |
| `command-ui-perform-reply.json` | an extension → server reply to `ui.perform` |
| `command-http-send-reply.json` | an extension → server reply to `http.send` |

The test skips itself while this directory holds no `.json` files, so an empty
directory does not block the backend track. Once a file exists it is checked, and
a file that does not parse fails the build.
