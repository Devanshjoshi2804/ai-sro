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
  {
    text = "",
    hidden = false,
    className = "",
    role = "",
    open = true,
    value = "",
  } = {},
) {
  return {
    kind,
    role,
    className,
    open,
    value,
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
    if (css.includes("progressbar"))
      return one.role === "progressbar" || /x-mask/.test(one.className);
    return (
      one.kind === "dialog" ||
      one.role === "dialog" ||
      one.role === "alertdialog" ||
      /x-message-box|modal show/.test(one.className)
    );
  };
  globalThis.document = {
    readyState: "complete",
    querySelectorAll: (css) => all.filter((one) => matches(one, css)),
  };
  return all;
}

const { whatIsOnThisPage, A_LOGIN, A_DIALOG, K_SAID } =
  await import("./whats-on-screen.js");
const { STILL_COMING } = await import("./whats-on-screen.js");
const ASK = {
  login: A_LOGIN,
  dialog: A_DIALOG,
  loading: STILL_COMING,
  cap: K_SAID,
};

test("a password box is a login and nothing else has to be", () => {
  page(el("password"));

  assert.equal(whatIsOnThisPage(ASK).signed_out, true);
});

test("an empty password box says so, and never what is in a filled one", () => {
  // The run engine's evidence that credentials were refused: the form came
  // back EMPTY after they were submitted. A form still holding what was typed
  // is a submit in flight. Only the fact of emptiness leaves the page.
  page(el("password"));
  assert.equal(whatIsOnThisPage(ASK).credential_empty, true);

  page(el("password", { value: "hunter2" }));
  const said = whatIsOnThisPage(ASK);
  assert.equal(said.credential_empty, false);
  assert.ok(!JSON.stringify(said).includes("hunter2"));
});

test("a hidden empty password box is not an empty login", () => {
  page(el("password", { hidden: true }));

  assert.equal(whatIsOnThisPage(ASK).credential_empty, false);
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

test("a page with none of them says none of them", () => {
  page(el("text"), el("button"));

  assert.deepEqual(whatIsOnThisPage(ASK), {
    signed_out: false,
    credential_empty: false,
    dialog: "",
    loading: false,
  });
});

test("a document that has not finished is still coming", () => {
  // What a half-drawn screen needs is a moment, and every rung of the ladder
  // spent on it is a model call answering a question about a page that was not
  // there yet.
  page(el("text"));
  globalThis.document.readyState = "loading";

  assert.equal(whatIsOnThisPage(ASK).loading, true);
});

test("a spinner over a finished document is still coming too", () => {
  // The case `readyState` cannot answer: a single-page application finished
  // its document minutes ago and is now fetching the screen, and `readyState`
  // has said `complete` the whole time.
  page(el("div", { className: "x-mask-loading" }));

  assert.equal(whatIsOnThisPage(ASK).loading, true);
});

test("a spinner nobody can see is not a page still coming", () => {
  page(el("div", { className: "x-mask-loading", hidden: true }));

  assert.equal(whatIsOnThisPage(ASK).loading, false);
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
