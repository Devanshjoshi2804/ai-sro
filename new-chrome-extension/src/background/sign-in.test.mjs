// Self-check for the one command that carries a secret.
//
// A tiny document rather than the panel's fake: what this reads is
// `querySelectorAll` and what it writes is `value` and three events, so the
// document it needs is a list of elements that answer a selector.
//
// Run with `node src/background/sign-in.test.mjs`.

import assert from "node:assert";

const tests = [];
const test = (name, fn) => tests.push([name, fn]);
let failed = 0;

/** One box on a page, remembering what was done to it. */
function box(
  kind,
  { name = "", id = "", autocomplete = "", disabled = false } = {},
) {
  return {
    kind,
    name,
    id,
    autocomplete,
    disabled,
    value: "",
    focused: false,
    events: [],
    clicks: 0,
    offsetParent: {},
    focus() {
      this.focused = true;
    },
    click() {
      this.clicks += 1;
    },
    dispatchEvent(event) {
      this.events.push(event.type);
    },
    getClientRects: () => [{}],
  };
}

/** The smallest document that can answer the four selectors a login uses. */
function page(...boxes) {
  const matches = (el, css) => {
    if (css.includes("one-time-code") || css.includes("otp"))
      return (
        el.autocomplete === "one-time-code" ||
        /otp|mfa/i.test(el.name) ||
        /verification/i.test(el.id)
      );
    if (css.includes("password")) return el.kind === "password" && !el.disabled;
    if (css.includes("submit") || css.includes("#next"))
      return el.kind === "submit" && !el.disabled;
    return ["email", "text", "tel"].includes(el.kind) && !el.disabled;
  };
  globalThis.document = {
    querySelectorAll: (css) => boxes.filter((el) => matches(el, css)),
  };
  globalThis.Event = class {
    constructor(type) {
      this.type = type;
    }
  };
  return boxes;
}

const { fillTheLoginForm, whatTheSignInCameTo } = await import("./sign-in.js");

const failure = (kind, detail) => ({
  ok: false,
  error_kind: kind,
  error_detail: detail,
});
const SAID = (where) => ({
  username: "operator",
  password: "a password nobody logs",
  where,
});
const { SIGN_IN } = await import("./sign-in.js");

test("both boxes are filled before either is submitted", () => {
  // Keycloak puts the username and the password on one form, and a driver that
  // filled whichever it found first submitted a password with no username --
  // five times, because the page came back empty and it did the same again.
  const [user, secret, go] = page(box("text"), box("password"), box("submit"));

  const done = fillTheLoginForm(SAID(SIGN_IN));

  assert.equal(user.value, "operator");
  assert.equal(secret.value, "a password nobody logs");
  assert.equal(go.clicks, 1);
  assert.deepEqual(done.did, [
    "entered the username",
    "entered the password",
    "submitted",
  ]);
});

test("a box is filled the way a framework notices", () => {
  // A value assigned without these is a box that looks full to a person and
  // empty to React, which then submits blank.
  const [user] = page(box("text"), box("submit"));

  fillTheLoginForm(SAID(SIGN_IN));

  assert.deepEqual(user.events, ["input", "change"]);
  assert.equal(user.focused, true);
});

test("a second factor is refused rather than attempted", () => {
  // A code sent to a phone has no answer in a vault, and pretending otherwise
  // leaves somebody watching a browser time out.
  const [, secret] = page(
    box("text", { autocomplete: "one-time-code" }),
    box("password"),
  );

  const done = fillTheLoginForm(SAID(SIGN_IN));

  assert.equal(done.mfa, true);
  assert.deepEqual(done.did, []);
  assert.equal(
    secret.value,
    "",
    "it typed a password at a page asking for a code",
  );
  assert.equal(
    whatTheSignInCameTo(done, failure).error_detail.includes("second factor"),
    true,
  );
});

test("a disabled box is not a box", () => {
  const [, live] = page(box("password", { disabled: true }), box("password"));

  fillTheLoginForm(SAID(SIGN_IN));

  assert.equal(live.value, "a password nobody logs");
});

test("a page that took nothing is refused rather than called done", () => {
  // Answering "done" about it would have the run retry a step against a screen
  // nothing has changed.
  page(box("checkbox"));

  const came = whatTheSignInCameTo(fillTheLoginForm(SAID(SIGN_IN)), failure);

  assert.equal(came.ok, false);
  assert.match(
    came.error_detail,
    /nothing on this page took a username or a password/,
  );
});

test("what comes back says what was done and never what was typed", () => {
  // The whole reason this file exists. A result carrying the value would put a
  // credential in a run record, in a rescue prompt, and in whatever reads it.
  page(box("text"), box("password"), box("submit"));

  const came = whatTheSignInCameTo(fillTheLoginForm(SAID(SIGN_IN)), failure);

  assert.equal(came.ok, true);
  assert.equal(JSON.stringify(came).includes("a password nobody logs"), false);
  assert.equal(JSON.stringify(came).includes("operator"), false);
});

for (const [name, fn] of tests) {
  try {
    await fn();
  } catch (error) {
    failed += 1;
    console.error(`  ✗ ${name}\n    ${error.message}`);
  }
}
if (failed) {
  console.error(`sign-in.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`sign-in.test.mjs: ok (${tests.length})`);
