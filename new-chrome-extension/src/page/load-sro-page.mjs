// The one place every test loads `page-code.js` from: its own source text,
// evaluated the way both of its real loaders evaluate it -- as a classic
// script's source, in a realm holding nothing else -- so what a test exercises
// is `globalThis.sroPage`, never an import. `page-code.js` has no `export`
// to import in the first place; this is the same trick `page-code.test.mjs`'s
// own self-check uses to prove that.
//
// Each call gets a fresh, isolated target rather than the real `globalThis`,
// so one test file's `sroPage` never leaks into another's and a suite that
// runs many cases never depends on `page-code.js`'s own re-injection guard
// (see the code note on `Object.defineProperty` in `page-code.js`) to keep
// working.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export const pageCodeSource = readFileSync(
  fileURLToPath(new URL("./page-code.js", import.meta.url)),
  "utf8",
);

export function loadSroPage(target = {}) {
  new Function("globalThis", pageCodeSource)(target);
  return target.sroPage;
}
