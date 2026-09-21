# Why `manifest.json` pins a `key`

Pins the extension id. Chrome derives an unpacked extension's id from the absolute path it was loaded from, so it differed per machine and per checkout -- which meant the console's allowed origins and the API's CORS list could not be defaulted, and every developer configured them by hand. With a key the id is onfmljaebeipeiinflhgdochbcjeoehl everywhere. The matching private key is not kept: it would only be needed to sign a .crx, and the Web Store issues its own.

Kept here rather than in the manifest. There is no comment syntax in
`manifest.json`, and a `_comment_key` field is not one: Chrome reserves
underscore-prefixed keys and answers an unknown one with
`Unrecognized manifest key '_comment_key'` on every single load, which is
a warning in the operator's face for a note meant for whoever reads the
repository.
