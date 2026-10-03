// Run with `node src/content/evidence.test.mjs`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const source = readFileSync(
  fileURLToPath(new URL("./recorder.generated.js", import.meta.url)),
  "utf8",
);

function body(name) {
  const at = source.indexOf(`const ${name} = (`);
  assert.notEqual(at, -1, `${name} is not in the generated recorder`);
  let depth = 0;
  for (let i = source.indexOf("{", source.indexOf("=>", at)); i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}" && (depth -= 1) === 0) return source.slice(at, i + 1);
  }
  throw new Error(`${name} never closes`);
}

export function lift(names, globals = {}) {
  const text = names.map(body).join(";\n");
  return new Function(
    ...Object.keys(globals),
    `const MAX_TEXT = 200; const MAX_VALUE = 4096; ${text}; return { ${names.join(", ")} };`,
  )(...Object.values(globals));
}

const el = (tag, attrs = {}, parent = null) => ({
  nodeType: 1,
  tagName: tag.toUpperCase(),
  parentElement: parent,
  getAttribute: (name) => (name in attrs ? attrs[name] : null),
});

test("the labelled ancestors are recorded outermost first", () => {
  const document = { getElementById: (id) => (id === "t" ? { innerText: "New Customer" } : null) };
  const { landmarksOf } = lift(["landmarkRole", "ownName", "landmarksOf"], { document });
  const dialog = el("div", { role: "dialog", "aria-labelledby": "t" });
  const form = el("form", { "aria-label": "Customer" }, dialog);
  const unnamed = el("section", {}, form);
  const input = el("input", {}, unnamed);

  assert.deepEqual(landmarksOf(input), [
    { role: "dialog", name: "New Customer" },
    { role: "form", name: "Customer" },
  ]);
});

test("a frame records where it sits, from the top down", () => {
  const { framePathOf } = lift(["framePathOf"]);
  const top = { frames: [] };
  top.parent = top;
  const shell = { parent: top, frames: [], location: { href: "https://wms.example/shell" } };
  const other = { parent: top, frames: [] };
  top.frames.push(other, shell);
  const screen = {
    parent: shell,
    frames: [],
    location: { href: "https://wms.example/screen?id=4", ancestorOrigins: ["https://wms.example"] },
  };
  shell.frames.push(screen);

  assert.deepEqual(framePathOf(screen), [
    { index: 1, url: "https://wms.example/shell" },
    { index: 0, url: "https://wms.example/screen?id=4" },
  ]);
  assert.deepEqual(framePathOf(top), []);
});

test("the state a gesture left never holds free text", () => {
  const window = { getComputedStyle: () => ({ visibility: "visible", display: "block" }) };
  const { stateOf } = lift(["isSecretName", "drawnMasked", "labelledText", "isSecretField", "roleOf", "settingOf", "stateOf"], {
    window,
    SECRET_WORDS: new Set(["password"]),
    wordsOf: (text) => String(text || "").toLowerCase().split(/[^a-z]+/).filter(Boolean),
  });
  const box = () => ({ width: 10, height: 10 });
  const control = (tag, attrs, props = {}) => ({
    nodeType: 1, isConnected: true, disabled: false, tagName: tag.toUpperCase(),
    type: attrs.type || (tag === "input" ? "text" : undefined),
    getAttribute: (name) => attrs[name] ?? null, getBoundingClientRect: box, ...props,
  });
  const valueOf = (el) => stateOf(el).value;

  assert.deepEqual(stateOf(control("input", { name: "code" }, { value: "GT2" })), {
    value: null, visible: true, enabled: true,
  });
  for (const type of ["search", "email", "tel", "url", "number", "password", "file"]) {
    assert.equal(valueOf(control("input", { type }, { value: "typed" })), null, type);
  }
  assert.equal(valueOf(control("textarea", {}, { value: "a note" })), null);
  assert.equal(valueOf(control("div", { contenteditable: "true" }, { innerText: "a note" })), null);
  for (const role of ["textbox", "searchbox", "combobox"]) {
    assert.equal(valueOf(control("div", { role }, { value: "typed" })), null, role);
  }
  assert.equal(valueOf(control("input", { type: "checkbox" }, { checked: true, value: "on" })), "checked");
  assert.equal(valueOf(control("input", { type: "radio" }, { checked: false, value: "on" })), "unchecked");
  assert.equal(valueOf(control("div", { role: "switch", "aria-checked": "true" })), "checked");
  const select = control("select", { name: "priority" }, {
    value: "b", selectedOptions: [{ label: "Second choice" }],
  });
  assert.equal(valueOf(select), "Second choice");
});

test("a control's position counts only siblings of its own kind", () => {
  const parent = { children: [] };
  const button = () => ({ nodeType: 1, tagName: "BUTTON", parentElement: parent, getAttribute: () => null });
  const input = { nodeType: 1, tagName: "INPUT", parentElement: parent, getAttribute: () => null };
  const [a, b] = [button(), button()];
  parent.children.push(a, input, b);
  const { siblingOf } = lift(["siblingOf"], { roleOf: (el) => (el.tagName === "BUTTON" ? "button" : "textbox") });
  assert.deepEqual(siblingOf(b), { index: 1, count: 2 });
});
