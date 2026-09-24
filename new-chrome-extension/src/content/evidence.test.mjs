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
