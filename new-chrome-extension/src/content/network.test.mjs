// Self-check for network.js's redaction: no test framework in this
// extension, so this runs network.js in a vm sandbox standing in for the
// isolated world (window.__sroIsSecretName, chrome.runtime.sendMessage) and
// asserts on what it sends. Run with `node src/content/network.test.mjs`.

import assert from "node:assert";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const SECRET = new Set([
  "password", "token", "secret", "otp", "apikey", "credential", "credentials",
]);
const isSecretName = (name) => {
  const words = (name || "")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .split(/[^A-Za-z]+/)
    .filter(Boolean)
    .map((w) => w.toLowerCase());
  return words.some((w) => SECRET.has(w)) || SECRET.has(words.join(""));
};

function run(rawEvents) {
  const sent = [];
  const sandbox = {
    window: {
      __sroIsSecretName: isSecretName,
      addEventListener: (type, fn) => {
        if (type === "sro:request") sandbox.__handler = fn;
      },
    },
    chrome: { runtime: { sendMessage: (msg) => (sent.push(msg), Promise.resolve({ ok: true })) } },
    location: { href: "https://wms.example.test/orders" },
    URLSearchParams,
    TextEncoder,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  const here = path.dirname(fileURLToPath(import.meta.url));
  vm.runInContext(readFileSync(path.join(here, "network.js"), "utf-8"), sandbox);
  for (const raw of rawEvents) sandbox.__handler({ detail: JSON.stringify(raw) });
  // Cross the vm-realm boundary: sandbox arrays/objects are foreign to this
  // realm's Array/Object, which trips deepStrictEqual's identity checks.
  return JSON.parse(JSON.stringify(sent));
}

const base = {
  request_id: "req_1",
  method: "POST",
  url: "https://wms.example.test/api/x",
  resource_type: "xhr",
  started_at: "2026-08-24T09:00:00.000Z",
  status: 200,
  status_text: "OK",
  duration_ms: 10,
  redirected: false,
  final_url: "https://wms.example.test/api/x",
  failure_reason: null,
};

// JSON body: a credential field is redacted, an ordinary one is kept.
{
  const [sent] = run([{
    ...base,
    request_headers: { "content-type": "application/json" },
    request_body_text: JSON.stringify({ code: "ACME", password: "hunter2" }),
    response_headers: {},
    response_body_text: null,
  }]);
  const body = sent.request.request_body;
  assert.deepStrictEqual(body.redacted_fields, ["password"]);
  assert.ok(!body.text.includes("hunter2"));
  assert.ok(body.text.includes("ACME"), "ordinary field survives redaction");
}

// Form body: same rule, urlencoded.
{
  const [sent] = run([{
    ...base,
    request_headers: { "content-type": "application/x-www-form-urlencoded" },
    request_body_text: "user=alice&token=abc123",
    response_headers: {},
    response_body_text: null,
  }]);
  const body = sent.request.request_body;
  assert.deepStrictEqual(body.redacted_fields, ["token"]);
  assert.ok(!body.text.includes("abc123"));
  assert.ok(body.text.includes("alice"));
}

// XML body: SOAP-style <Password> element redacted.
{
  const [sent] = run([{
    ...base,
    request_headers: { "content-type": "text/xml" },
    request_body_text: "<Login><User>alice</User><Password>hunter2</Password></Login>",
    response_headers: {},
    response_body_text: null,
  }]);
  const body = sent.request.request_body;
  assert.deepStrictEqual(body.redacted_fields, ["Password"]);
  assert.ok(!body.text.includes("hunter2"));
  assert.ok(body.text.includes("alice"));
}

// No body: request_body stays null rather than an empty object.
{
  const [sent] = run([{ ...base, request_headers: {}, request_body_text: null, response_headers: {}, response_body_text: null }]);
  assert.strictEqual(sent.request.request_body, null);
}

console.log("network.test.mjs: ok");
