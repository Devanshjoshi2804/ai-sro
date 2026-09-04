// The redaction the browser actually runs.
//
// This imports `sensitivity.module.js` -- the generated artefact the service
// worker loads -- rather than the Python it comes from, because the generated
// copy is what redacts a `webNavigation` URL. `test_generated_scripts_are_current.py`
// keeps it equal to its source; this keeps its behaviour honest.
//
// Run with `node src/content/sensitivity.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

import {
  isSecretHeader,
  isSecretName,
  redactShapes,
  redactUrl,
  shapesIn,
} from "./sensitivity.module.js";

const REDACTED = "«redacted»";

// --- Open item 4: OAuth hands the token back in the fragment ----------------

test("a token in the fragment is redacted, not stored raw", () => {
  // The implicit flow's whole answer arrives after the `#`. The backend
  // redacts bodies and headers but never URLs, so if this does not do it,
  // nothing does.
  assert.equal(
    redactUrl("https://wms.example/callback#access_token=ya29.abc&token_type=bearer"),
    `https://wms.example/callback#access_token=${REDACTED}&token_type=${REDACTED}`,
  );
});

test("a fragment carrying nothing secret comes back byte-identical", () => {
  const url = "https://wms.example/app#view=picking&facility=BLR1";
  assert.equal(redactUrl(url), url);
});

test("a query and a fragment are both judged, and each keeps its own bytes", () => {
  assert.equal(
    redactUrl("https://wms.example/app?facility=BLR%201&api_key=k#id_token=j.w.t&view=picking"),
    `https://wms.example/app?facility=BLR%201&api_key=${REDACTED}#id_token=${REDACTED}&view=picking`,
  );
});

test("a bare anchor is left exactly alone", () => {
  // `#section-heading` has no pairs in it. Splitting it on `&` and `=` would
  // be inventing structure the URL never had.
  for (const url of [
    "https://wms.example/docs#section-heading",
    "https://wms.example/docs?q=pick#section-heading",
    "https://wms.example/docs#",
    "https://wms.example/docs",
  ]) {
    assert.equal(redactUrl(url), url, url);
  }
});

test("a relative or unparseable URL is still left alone", () => {
  for (const url of ["/v1/orders#access_token=x", "", "not a url"]) {
    assert.equal(redactUrl(url), url, JSON.stringify(url));
  }
});

// --- Open item 3: six credential words the browser did not know -------------

test("a warehouse session is not a login session", () => {
  // The bare word `session` was added this session on a measurement over 217
  // field names from one tenant subset. Re-measured over 3,256 distinct real
  // names (the acme store plus knowledge-base/http/exchanges) it blanked three
  // live warehouse fields: in a WMS a session is a unit of picking work. The
  // credential meaning lives in the compounds instead, which cost nothing.
  for (const field of ["sessionGroup", "sessionNumber", "sessionTag"]) {
    assert.equal(isSecretName(field), false, `${field} is picking work, not a login`);
  }
  for (const field of ["sessionId", "sessionKey", "sessionToken", "JSESSIONID", "PHPSESSID"]) {
    assert.equal(isSecretName(field), true, `${field} reached storage`);
  }
});

test("an AWS-shaped body is a credential too", () => {
  // The vocabulary had exactly one compound in it, `apikey`, and neither
  // `access` nor `key` is a word here -- so every one of these reached the
  // store and the prompt verbatim. All measured at zero cost over the same
  // 3,256 real names.
  for (const field of [
    "accessKey",
    "secretAccessKey",
    "privateKey",
    "sshKey",
    "encryptionKey",
    "clientSecret",
    "idToken",
    "connectionString",
    "csrfToken",
  ]) {
    assert.equal(isSecretName(field), true, `${field} reached storage`);
  }
});

test("a session, cookie or SSO field name is a credential", () => {
  // `{"sessionId": "..."}` in a request body was redacted nowhere: these words
  // were in the header lists on both sides and in neither field list.
  for (const field of [
    "sessionId",
    "session_token",
    "Cookie",
    "jwt",
    "bearerToken",
    "sso_ticket",
    "saml_response",
    "samlAssertion",
  ]) {
    assert.equal(isSecretName(field), true, `${field} reached storage`);
  }
});

test("an all-caps acronym still hides the word inside it", () => {
  // Was the recorded ceiling and is now the behaviour: wordsOf() split on
  // lower-then-upper only, so `SAMLResponse` -- the literal field name of a
  // SAML HTTP-POST binding -- was one word "samlresponse" and matched nothing,
  // which made the word `saml` useless for the field it was added for. The
  // `([A-Z]{2,})([A-Z][a-z])` boundary in the shared splitter closes it.
  assert.equal(isSecretName("SAMLResponse"), true, "SAMLResponse reached storage");
  assert.equal(isSecretName("SSOToken"), true, "SSOToken reached storage");
  assert.equal(isSecretName("JWTToken"), true, "JWTToken reached storage");
  assert.equal(isSecretName("APIKey"), true, "APIKey reached storage");
});

test("a one-letter run is not an acronym", () => {
  // The reason the boundary is `{2,}` and not `+`. "Pick N Pass" is a warehouse
  // operation: `([A-Z]+)([A-Z][a-z])` splits the lone N off and leaves `Pass`
  // bare, blanking two real field names. Measured over 3,270 distinct field,
  // header and query-parameter names from the acme store plus
  // knowledge-base/http/exchanges, `{2,}` changes none of them and `+` changes
  // exactly these two -- both wrongly.
  for (const field of ["pickNPassAutoDropLocation", "pickNPassDropWorkZone"]) {
    assert.equal(isSecretName(field), false, `${field} is a warehouse operation, not a credential`);
  }
});

test("the real field names those six sit inside are still kept", () => {
  // Measured over the 217 distinct field names in this tenant's captured
  // evidence: none of the six matches as a whole word, and these five are what
  // a substring rule would have blanked instead. They are the reason the rule
  // must stay whole-word.
  for (const field of [
    "addressId",
    "codAddressId",
    "shipperAddressId",
    "residentialAddress",
    "NLSSORTSetting",
    "sessions_per_day",
  ]) {
    assert.equal(isSecretName(field), false, `${field} is business data, not a credential`);
  }
});

test("a session token in a query string goes the same way as one in a header", () => {
  // `jsessionid` is one word and the whole-word rule does not split it, so it
  // used to pass through -- a live Java servlet session in a stored URL. It is
  // in the vocabulary as that one word now, measured at zero cost over 3,256
  // real names. `session_id` below still matches through the joined form, which
  // is what lets the bare word `session` stay out (it blanked `sessionGroup`).
  assert.equal(
    redactUrl("https://wms.example/app?jsessionid=A1B2&facility=BLR1"),
    `https://wms.example/app?jsessionid=${REDACTED}&facility=BLR1`,
    "a Java servlet session id reached storage",
  );
  assert.equal(
    redactUrl("https://wms.example/app?session_id=A1B2&facility=BLR1"),
    `https://wms.example/app?session_id=${REDACTED}&facility=BLR1`,
  );
});

test("an HTTP/2 pseudo-header is the request line, not a credential", () => {
  // `:authority` is the host and contains the hint "auth", so the hint list
  // redacted it -- a stored request that had lost the one field saying where it
  // went. Decided by the leading colon before any hint is consulted, on both
  // sides: classify_header does the same first.
  for (const name of [":method", ":path", ":scheme", ":authority"]) {
    assert.equal(isSecretHeader(name), false, `${name} is the request line`);
  }
  // And the hints still do their job on real header names.
  assert.equal(isSecretHeader("X-Vault-Token"), true);
  assert.equal(isSecretHeader("X-Auth-Key"), true);
});

// A JWT nobody would write down: real base64url header and payload, so the
// shape is genuine, and the word `not-a-signature` where the signature goes.
const FAKE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJub2JvZHkifQ.not-a-signature";

test("a credential in a path segment has no name to be judged by", () => {
  assert.equal(
    redactUrl(`https://wms.example/reset/${FAKE_JWT}?facility=BLR1`),
    `https://wms.example/reset/${REDACTED}?facility=BLR1`,
  );
});

test("the shape pass leaves a URL carrying no credential byte-identical", () => {
  const url = "https://wms.example/app?tag=a&tag=b&q=a+b&note=two%20words#view=picking";
  assert.equal(redactUrl(url), url);
});

test("shapesIn names every rule that fired, once each, first seen first", () => {
  assert.deepEqual(shapesIn(`${FAKE_JWT} AKIAIOSFODNN7EXAMPLE ${FAKE_JWT}`), [
    "jwt",
    "aws_key_id",
  ]);
  assert.deepEqual(shapesIn("facility=BLR1&limit=200"), []);
});

test("a private key loses its key material and not just its header", () => {
  const pem =
    "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIsomething\n-----END EC PRIVATE KEY-----";
  assert.equal(redactShapes(`note\n${pem}\nend`), `note\n${REDACTED}\nend`);
});
