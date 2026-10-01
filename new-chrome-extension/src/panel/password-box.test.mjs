// A run that cannot sign in asks for the password on its own card.
//
// The box is one function for every card that draws a run (Home's mail card,
// the run card), so the property is held once: what is typed goes to the
// worker through `onPassword` and nowhere else, the field is emptied on the
// press, and the words say what happened to it.
//
// Run with `node src/panel/password-box.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

import { asMarkup, install, of, words } from "./test-support/fake-document.mjs";

install();

const { passwordBox, standingPassword } = await import("./password-box.js");

const question = {
  id: "q_1",
  kind: "password",
  text: "clerk at login.idp.example has no usable password. Enter it on the run's card.",
  origin: "login.idp.example",
  username: "clerk",
  field: "password",
};

const press = (box, label) =>
  of(box, "button").find((button) => button.textContent === label);

test("it says whose password and where, and offers keeping or lending it", () => {
  const box = passwordBox(question, { runId: "run_1", onPassword: () => ({ ok: true }) });

  assert.match(
    words(box),
    /needs your password for login\.idp\.example \(clerk\)/,
  );
  const field = of(box, "input")[0];
  assert.equal(field.type, "password");
  assert.equal(field.autocomplete, "off");
  assert.ok(press(box, "Save for next time"));
  assert.ok(press(box, "Just this once"));
});

test("a press sends the question, the value and the choice, and empties the field", async () => {
  const sent = [];
  const box = passwordBox(question, {
    runId: "run_1",
    onPassword: (one) => {
      sent.push(one);
      return { ok: true };
    },
  });
  const field = of(box, "input")[0];

  field.value = "not-in-any-fixture-4d1a";
  await press(box, "Save for next time").listeners.click[0]();
  field.value = "lent-4d1a";
  await press(box, "Just this once").listeners.click[0]();

  assert.deepEqual(sent, [
    { runId: "run_1", questionId: "q_1", value: "not-in-any-fixture-4d1a", keep: true },
    { runId: "run_1", questionId: "q_1", value: "lent-4d1a", keep: false },
  ]);
  assert.equal(field.value, "", "the password was left sitting in the panel");
  assert.match(words(box), /carries on/);
  assert.ok(!words(box).includes("lent-4d1a"));
  assert.deepEqual(asMarkup, [], "a password reached the page as markup");
});

test("an empty box sends nothing, and a refusal says why", async () => {
  const sent = [];
  const box = passwordBox(question, {
    runId: "run_1",
    onPassword: (one) => {
      sent.push(one);
      return { ok: false, error: "the vault did not answer" };
    },
  });
  const save = press(box, "Save for next time");

  await save.listeners.click[0]();
  assert.deepEqual(sent, [], "an empty box was sent as a password");

  of(box, "input")[0].value = "x";
  await save.listeners.click[0]();
  assert.match(words(box), /could not be saved: the vault did not answer/);
  assert.equal(save.disabled, false, "a failed press left the button dead");
});

test("only a standing password question that names its account draws a box", () => {
  assert.equal(standingPassword({ question }), question);
  assert.equal(standingPassword({ question: { ...question, kind: "step" } }), null);
  assert.equal(standingPassword({ question: null }), null);
  assert.equal(standingPassword({}), null);
  // Asked before it named its account: the backend refuses it, so no box.
  assert.equal(standingPassword({ question: { ...question, origin: "" } }), null);
});
