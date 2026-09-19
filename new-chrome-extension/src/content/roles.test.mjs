// What kind of control the recorder thinks an element is.
//
// `getAttribute('role')` reads only what an author wrote down, and almost
// nobody writes `role="button"` on a `<button>`. So the one identity this
// system has for a control with no framework component and no test id was
// `name|<label>` -- which reads exactly the same as an accessible name on a
// `<div>`, and a `<div>` in a mailbox is labelled with the mail.
//
// Measured on the deployment 2026-09-20 over 732 gestures: 132 identities came
// through that branch and they are two different things wearing one shape.
// `Username or email` (30), `Sign In` (14) and `Subject` (5) are controls.
// `Devansh Joshi` (17), `Tanisha Pradhan` (13), `104` (7) and `2,486` are a
// sender, a subject and a message count -- content, on a div, changing with
// every mail, minting another job each time. `Reply to Email` reached five
// rows that way.
//
// Read out of the SHIPPED file rather than a copy of the rule: this is a
// generated artefact, and a test against a second copy of the table would pass
// on the day a regeneration dropped it.
//
// Run with `node src/content/roles.test.mjs`.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const source = readFileSync(
  fileURLToPath(new URL("./recorder.generated.js", import.meta.url)),
  "utf8",
);

/** The helper as it ships, lifted out by matching its braces. */
function lift(name) {
  const at = source.indexOf(`const ${name} = (el) => {`);
  assert.notEqual(at, -1, `${name} is not in the generated recorder`);
  let depth = 0;
  for (let i = source.indexOf("{", at); i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        return new Function(`${source.slice(at, i + 1)}; return ${name};`)();
      }
    }
  }
  throw new Error(`${name} never closes`);
}

const roleOf = lift("roleOf");

const el = (tag, attrs = {}) => ({
  tagName: tag.toUpperCase(),
  getAttribute: (name) => (name in attrs ? attrs[name] : null),
  hasAttribute: (name) => name in attrs,
});

test("what the page wrote down wins", () => {
  assert.equal(roleOf(el("div", { role: "alert" })), "alert");
  assert.equal(roleOf(el("input", { role: "combobox" })), "combobox");
});

test("a control keeps the role its tag already implies", () => {
  assert.equal(roleOf(el("button")), "button");
  assert.equal(roleOf(el("a", { href: "/x" })), "link");
  assert.equal(roleOf(el("select")), "combobox");
  assert.equal(roleOf(el("textarea")), "textbox");
  assert.equal(roleOf(el("input")), "textbox", "a bare input is a text input");
  assert.equal(roleOf(el("input", { type: "email" })), "textbox");
  assert.equal(roleOf(el("input", { type: "checkbox" })), "checkbox");
  assert.equal(roleOf(el("input", { type: "submit" })), "button");
});

test("the sign-in field the whole Keycloak job is identified by", () => {
  // `Username or email` came through as `name|Username or email` -- an
  // identity indistinguishable from a mail subject. It is an `<input>`.
  assert.equal(roleOf(el("input", { "aria-label": "Username or email" })), "textbox");
});

test("a password field is a textbox, and is kept out by redaction not by this", () => {
  assert.equal(roleOf(el("input", { type: "password" })), "textbox");
});

test("content is still nothing, which is what lets it fall past `name|`", () => {
  // A sender's name on a div, a message count on a span. These are what minted
  // a job per mail, and they must not acquire a role here.
  assert.equal(roleOf(el("div", { "aria-label": "Devansh Joshi" })), null);
  assert.equal(roleOf(el("span")), null);
  assert.equal(roleOf(el("td")), null);
  assert.equal(roleOf(el("a")), null, "an anchor with no href is not a link");
});
