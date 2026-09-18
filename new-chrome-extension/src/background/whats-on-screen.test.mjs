// Self-check for what a page says about itself when a step cannot find its
// control.
//
// The rule under test is the one the whole file exists for: STRUCTURE, never
// words. A screen that mentions a password is not a login, and a column headed
// "Dialog" is not a dialog.
//
// Run with `node src/background/whats-on-screen.test.mjs`.

import assert from "node:assert";

const tests = [];
const test = (name, fn) => tests.push([name, fn]);
let failed = 0;

/** One element, as much of one as these selectors read. */
function el(
  kind,
  { text = "", hidden = false, className = "", role = "", open = true } = {},
) {
  return {
    kind,
    role,
    className,
    open,
    innerText: text,
    textContent: text,
    offsetParent: hidden ? null : {},
    getClientRects: () => (hidden ? [] : [{}]),
  };
}

/** The smallest document that can answer the two selectors this reads. */
function page(...all) {
  const matches = (one, css) => {
    if (css.includes("password"))
      return one.kind === "password" || one.kind === "current-password";
    return (
      one.kind === "dialog" ||
      one.role === "dialog" ||
      one.role === "alertdialog" ||
      /x-message-box|modal show/.test(one.className)
    );
  };
  globalThis.document = {
    querySelectorAll: (css) => all.filter((one) => matches(one, css)),
  };
  return all;
}

const { whatIsOnThisPage, A_LOGIN, A_DIALOG, K_SAID } =
  await import("./whats-on-screen.js");
const ASK = { login: A_LOGIN, dialog: A_DIALOG, cap: K_SAID };

test("a password box is a login and nothing else has to be", () => {
  page(el("password"));

  assert.equal(whatIsOnThisPage(ASK).signed_out, true);
});

test("a page that only talks about passwords is not a login", () => {
  // Any heuristic on words fires on a working screen eventually, and a run
  // that stopped saying "you are signed out" in front of a form that was fine
  // would be worse than one that said nothing.
  page(el("text", { text: "Password policy: 8 characters" }));

  assert.equal(whatIsOnThisPage(ASK).signed_out, false);
});

test("a dialog is read for what it says, because that is the answer", () => {
  // `Existing Carriers duplicate check is SERVER-side: the form accepts the
  // click and only then shows an in-app 'Record already exists' modal.`
  page(el("dialog", { text: "Record already exists" }));

  assert.equal(whatIsOnThisPage(ASK).dialog, "Record already exists");
});

test("a dialog nobody can see is not on the screen", () => {
  // Frameworks keep their modals in the document and hide them. A run that
  // read one of those would report a dialog on every screen that has ever
  // shown one.
  page(el("dialog", { text: "Record already exists", hidden: true }));

  assert.equal(whatIsOnThisPage(ASK).dialog, "");
});

test("whitespace in a dialog is not what it said", () => {
  page(
    el("dialog", { text: "  Record already   exists.\n\n  Choose another. " }),
  );

  assert.equal(
    whatIsOnThisPage(ASK).dialog,
    "Record already exists. Choose another.",
  );
});

test("a dialog with a page inside it is cut to what a person reads", () => {
  // A wrapper often contains the screen behind it, and "what the dialog said"
  // would then be the whole screen read out into a step record.
  page(el("dialog", { text: "x".repeat(4000) }));

  assert.equal(whatIsOnThisPage(ASK).dialog.length, K_SAID);
});

test("a page with neither says neither", () => {
  page(el("text"), el("button"));

  assert.deepEqual(whatIsOnThisPage(ASK), { signed_out: false, dialog: "" });
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
  console.error(`whats-on-screen.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`whats-on-screen.test.mjs: ok (${tests.length})`);
