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

/** Runs the real generated rules, so this checks what actually ships rather
 * than a hand-written stand-in that could disagree with it. */
function makeSandbox({ withRules = true } = {}) {
  const sent = [];
  const sandbox = {
    window: {
      addEventListener: (type, fn) => {
        if (type === "sro:request") sandbox.__handler = fn;
      },
    },
    chrome: { runtime: { sendMessage: (msg) => (sent.push(msg), Promise.resolve({ ok: true })) } },
    location: { href: "https://wms.example.test/orders" },
    URL,
    URLSearchParams,
    TextEncoder,
    sent,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  if (withRules) vm.runInContext(read("sensitivity.generated.js"), sandbox);
  vm.runInContext(read("network.js"), sandbox);
  return sandbox;
}

function run(raw, options) {
  const sandbox = makeSandbox(options);
  sandbox.__handler({ detail: JSON.stringify(raw) });
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
  sandbox.__handler({ detail: JSON.stringify({ nonsense: true }) });
  sandbox.__handler({ detail: "not json at all" });
  sandbox.__handler({ detail: 42 });
  assert.strictEqual(sandbox.sent.length, 0, "malformed records are not forwarded");
}

console.log("network.test.mjs: ok");
