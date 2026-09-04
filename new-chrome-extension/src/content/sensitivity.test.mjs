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

import { isSecretName, redactUrl } from "./sensitivity.module.js";

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
  // Known ceiling, recorded rather than hidden: wordsOf() splits on
  // lower-then-upper only, so `SAMLResponse` -- the literal field name of a
  // SAML HTTP-POST binding -- is one word "samlresponse" and does not match.
  // The same gap predates these six: `SSOToken` and `APIKey` are one word too.
  // Fixing it means adding an ACRONYM|Word boundary to the shared splitter in
  // sro/domain/recording/sensitivity.py, which changes how every field name in
  // the deployment is judged and wants measuring against captured evidence
  // first. See .superpowers/sdd/2026-09-04-the-miner/open-1-report.md.
  assert.equal(isSecretName("SAMLResponse"), false);
  assert.equal(isSecretName("SSOToken"), false);
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
  assert.equal(
    redactUrl("https://wms.example/app?jsessionid=A1B2&facility=BLR1"),
    `https://wms.example/app?jsessionid=A1B2&facility=BLR1`,
    "jsessionid is one word, not two -- the whole-word rule does not split it",
  );
  assert.equal(
    redactUrl("https://wms.example/app?session_id=A1B2&facility=BLR1"),
    `https://wms.example/app?session_id=${REDACTED}&facility=BLR1`,
  );
});
