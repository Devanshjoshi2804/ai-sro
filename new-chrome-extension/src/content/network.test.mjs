// Self-check for network.js's redaction: no test framework in this
// extension, so this runs network.js in a vm sandbox standing in for the
// isolated world (the generated credential rules, chrome.runtime.sendMessage)
// and asserts on what it sends. Run with `node src/content/network.test.mjs`.

import assert from "node:assert";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const read = (name) => readFileSync(path.join(here, name), "utf-8");

const NONCE = "test-realm-nonce";

/** Runs the real generated rules, so this checks what actually ships rather
 * than a hand-written stand-in that could disagree with it.
 *
 * `window` here is a small event target because network.js does a handshake
 * with the page-realm patch on load; `answerHandshake` plays that half. With
 * it left out, nothing has ever proved it came from us, which is the whole
 * point of the exchange. */
function makeSandbox({ withRules = true, answerHandshake = true } = {}) {
  const sent = [];
  const listeners = {};
  const sandbox = {
    window: {
      addEventListener: (type, fn) => {
        (listeners[type] ||= []).push(fn);
      },
      removeEventListener: (type, fn) => {
        listeners[type] = (listeners[type] || []).filter((each) => each !== fn);
      },
      dispatchEvent: (event) => {
        for (const fn of [...(listeners[event.type] || [])]) fn(event);
        return true;
      },
    },
    CustomEvent: class {
      constructor(type, init) {
        this.type = type;
        this.detail = init?.detail;
      }
    },
    chrome: { runtime: { sendMessage: (msg) => (sent.push(msg), Promise.resolve({ ok: true })) } },
    location: { href: "https://wms.example.test/orders" },
    URL,
    URLSearchParams,
    TextEncoder,
    setTimeout,
    clearTimeout,
    sent,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  if (withRules) vm.runInContext(read("sensitivity.generated.js"), sandbox);
  if (answerHandshake) {
    // The page-realm half, answering the request network.js makes on load.
    (listeners["sro:need-hello"] ||= []).push(() => {
      sandbox.window.dispatchEvent(new sandbox.CustomEvent("sro:hello", { detail: NONCE }));
    });
  }
  vm.runInContext(read("network.js"), sandbox);
  sandbox.__fire = (raw) =>
    sandbox.window.dispatchEvent(
      new sandbox.CustomEvent("sro:request", { detail: JSON.stringify(raw) }),
    );
  return sandbox;
}

function run(raw, options) {
  const sandbox = makeSandbox(options);
  sandbox.__fire({ __from: NONCE, ...raw });
  // Cross the vm-realm boundary: sandbox arrays/objects are foreign to this
  // realm's Array/Object, which trips deepStrictEqual's identity checks.
  return JSON.parse(JSON.stringify(sandbox.sent));
}

const base = {
  request_id: "req_abc_0",
  method: "POST",
  url: "https://wms.example.test/api/x",
  resource_type: "xhr",
  started_at: "2026-08-24T09:00:00.000Z",
  request_headers: {},
  response_headers: {},
  request_body_text: null,
  response_body_text: null,
  request_body_truncated: false,
  response_body_truncated: false,
  status: 200,
  status_text: "OK",
  duration_ms: 10,
  redirected: false,
  final_url: "https://wms.example.test/api/x",
  failure_reason: null,
};

// JSON body: a credential field is redacted, an ordinary one is kept.
{
  const [sent] = run({
    ...base,
    request_headers: { "content-type": "application/json" },
    request_body_text: JSON.stringify({ code: "ACME", password: "hunter2" }),
  });
  const body = sent.request.request_body;
  assert.deepStrictEqual(body.redacted_fields, ["password"]);
  assert.ok(!body.text.includes("hunter2"));
  assert.ok(body.text.includes("ACME"), "ordinary field survives redaction");
}

// Form body: same rule, urlencoded.
{
  const [sent] = run({
    ...base,
    request_headers: { "content-type": "application/x-www-form-urlencoded" },
    request_body_text: "user=alice&token=abc123",
  });
  const body = sent.request.request_body;
  assert.deepStrictEqual(body.redacted_fields, ["token"]);
  assert.ok(!body.text.includes("abc123"));
  assert.ok(body.text.includes("alice"));
}

// XML body: SOAP-style <Password> element redacted.
{
  const [sent] = run({
    ...base,
    request_headers: { "content-type": "text/xml" },
    request_body_text: "<Login><User>alice</User><Password>hunter2</Password></Login>",
  });
  const body = sent.request.request_body;
  assert.deepStrictEqual(body.redacted_fields, ["Password"]);
  assert.ok(!body.text.includes("hunter2"));
  assert.ok(body.text.includes("alice"));
}

// No body: request_body stays null rather than an empty object.
{
  const [sent] = run(base);
  assert.strictEqual(sent.request.request_body, null);
}

// A truncated body cannot be parsed, so it cannot be redacted, so it is not
// kept. This is the fail-open path that used to ship credentials verbatim.
{
  const [sent] = run({
    ...base,
    request_headers: { "content-type": "application/json" },
    request_body_text: '{"code":"ACME","password":"hunter2"',
    request_body_truncated: true,
  });
  const body = sent.request.request_body;
  assert.strictEqual(body.text, null, "a truncated body is dropped, not stored");
  assert.ok(!JSON.stringify(sent).includes("hunter2"));
  assert.deepStrictEqual(body.redacted_fields, ["«whole body: could not be parsed to redact»"]);
}

// Unparseable-but-complete JSON is the same case: no promise can be made.
{
  const [sent] = run({
    ...base,
    request_headers: { "content-type": "application/json" },
    request_body_text: ')]}\',\n{"password":"hunter2"}',
  });
  assert.strictEqual(sent.request.request_body.text, null);
  assert.ok(!JSON.stringify(sent).includes("hunter2"));
}

// With the credential rules absent, nothing is claimed to be clean.
{
  const [sent] = run(
    {
      ...base,
      request_headers: { "content-type": "application/json" },
      request_body_text: JSON.stringify({ password: "hunter2" }),
    },
    { withRules: false },
  );
  assert.strictEqual(sent.request.request_body.text, null, "fails closed with no rules loaded");
  assert.ok(!JSON.stringify(sent).includes("hunter2"));
}

// Credential headers lose their values and keep their names.
{
  const [sent] = run({
    ...base,
    request_headers: {
      Authorization: "Bearer live-session-token",
      "CSRF-ENCRYPT-TOKEN": "abc",
      "Content-Type": "application/json",
      "X-Facility": "WH1",
    },
  });
  const headers = sent.request.request_headers;
  assert.strictEqual(headers.Authorization, "«redacted»");
  assert.strictEqual(headers["CSRF-ENCRYPT-TOKEN"], "«redacted»");
  assert.strictEqual(headers["Content-Type"], "application/json", "semantic headers are kept");
  assert.strictEqual(headers["X-Facility"], "WH1", "business headers are kept");
  assert.ok(!JSON.stringify(sent).includes("live-session-token"));
}

// A credential in the query string is a credential.
{
  const [sent] = run({ ...base, url: "https://wms.example.test/api/x?user=alice&token=sekrit" });
  assert.ok(!sent.request.url.includes("sekrit"));
  assert.ok(sent.request.url.includes("alice"));
}

// The passive tier cannot see redirect hops, so it claims none.
{
  const [sent] = run({ ...base, redirected: true, final_url: "https://elsewhere.test/y" });
  assert.deepStrictEqual(sent.request.redirect_chain, []);
}

// A page can dispatch this event too. Junk is refused rather than forwarded.
{
  const sandbox = makeSandbox();
  sandbox.__fire({ nonsense: true });
  sandbox.window.dispatchEvent(new sandbox.CustomEvent("sro:request", { detail: "not json" }));
  sandbox.window.dispatchEvent(new sandbox.CustomEvent("sro:request", { detail: 42 }));
  assert.strictEqual(sandbox.sent.length, 0, "malformed records are not forwarded");
}

// A well-formed record that did not come from our patch is refused: a page
// can dispatch this event as easily as we can, and a fabricated exchange
// becomes a candidate skill somebody is offered.
{
  const sandbox = makeSandbox();
  sandbox.__fire({ ...base, __from: "guessed-wrong" });
  sandbox.__fire({ ...base }); // no provenance at all
  assert.strictEqual(sandbox.sent.length, 0, "a forged exchange was forwarded");
  sandbox.__fire({ ...base, __from: NONCE });
  assert.strictEqual(sandbox.sent.length, 1, "the genuine record still goes");
}

// With no handshake completed, nothing is accepted rather than everything.
{
  const sandbox = makeSandbox({ answerHandshake: false });
  sandbox.__fire({ ...base, __from: NONCE });
  assert.strictEqual(sandbox.sent.length, 0, "records were accepted with no handshake");
}

console.log("network.test.mjs: ok");



// A handshake that never happened is reported, not endured in silence.
//
// Reloading the extension replaces this half with a fresh one that knows no
// realm, while the page-realm half that could tell it is the *old* one, which
// answered its single hello long ago and stopped listening. The patch is still
// installed and still emitting; every record it sends is dropped here.
//
// It cannot be repaired: the patch lives in the page's own realm, so once page
// scripts are running there is no channel to it a page cannot also read and
// write. Answering a hello later hands the secret to whoever asked, and a
// forged exchange becomes a candidate skill an operator is offered --
// `test_the_page_cannot_forge_an_exchange_into_the_evidence_plane` holds that
// line and should be read beside this.
//
// So the tab says so, and teaching refuses to start in it. Silence here cost an
// operator two demonstrations: gestures recorded, every call dropped, nothing
// anywhere saying why.
{
  const orphaned = makeSandbox({ answerHandshake: false });
  await new Promise((resolve) => setTimeout(resolve, 1300));
  const said = JSON.parse(JSON.stringify(orphaned.sent));
  assert.ok(
    said.some((message) => message.kind === "calls-not-recordable"),
    "a tab that never completed the handshake said nothing about it",
  );

  // And a tab that did complete it says nothing, or the panel learns to ignore
  // the one message that matters.
  const whole = makeSandbox({ answerHandshake: true });
  await new Promise((resolve) => setTimeout(resolve, 1300));
  const quiet = JSON.parse(JSON.stringify(whole.sent));
  assert.ok(
    !quiet.some((message) => message.kind === "calls-not-recordable"),
    "a tab whose handshake succeeded reported itself broken",
  );
}
