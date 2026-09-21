// Every name one panel module imports from another is one that module exports.
//
// The panel blanked once, completely, for this: `panel.js` imported
// `renderNudge` from `ledger.js`, which exports no such thing -- the helper of
// that name lives in a test file. A named import that does not resolve is a
// LINK error, so the module never runs at all: no strip, no cards, no
// composer, no error anywhere a person would look. 2026-09-16.
//
// Nothing else could have caught it. `panel.test.mjs` concatenates these files
// and strips every `import` line to stand them up in one scope, which is what
// makes that harness possible and is exactly why it cannot see this. So the
// check is static and lives here: read the import lines, read the exports, and
// compare.
//
// Run with `node src/panel/imports.test.mjs`.

import assert from "node:assert";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, "..");

/** The names a file exports, by the two forms this codebase uses. */
function exported(source) {
  const names = new Set();
  for (const [, name] of source.matchAll(/^export\s+(?:async\s+)?function\s+([A-Za-z0-9_$]+)/gm)) {
    names.add(name);
  }
  for (const [, name] of source.matchAll(/^export\s+(?:const|let|class)\s+([A-Za-z0-9_$]+)/gm)) {
    names.add(name);
  }
  // `export { a, b, c }` at the foot, which is how the generated sensitivity
  // module says what it offers.
  for (const [, listed] of source.matchAll(/^export\s*\{([^}]+)\}\s*;?\s*$/gm)) {
    for (const one of listed.split(",")) {
      const name = one.trim().split(/\s+as\s+/).pop().trim();
      if (name) names.add(name);
    }
  }
  return names;
}

/** Every `import { a, b } from "./x.js"` in a file, as [specifier, names]. */
function imports(source) {
  return [...source.matchAll(/^import\s+\{([^}]+)\}\s+from\s+"([^"]+)"/gm)].map(([, named, from]) => [
    from,
    named
      .split(",")
      .map((one) => one.trim().split(/\s+as\s+/)[0].trim())
      .filter(Boolean),
  ]);
}

const files = [];
for (const dir of ["panel", "background", "content"]) {
  for (const name of readdirSync(path.join(root, dir))) {
    if (name.endsWith(".js")) files.push(path.join(dir, name));
  }
}

let failed = 0;
for (const file of files) {
  const source = readFileSync(path.join(root, file), "utf-8");
  for (const [from, names] of imports(source)) {
    // Only this codebase's own modules: a bare specifier is a package and a
    // package's exports are its business.
    if (!from.startsWith(".")) continue;
    const target = path.join(path.dirname(path.join(root, file)), from);
    let has;
    try {
      has = exported(readFileSync(target, "utf-8"));
    } catch {
      failed += 1;
      console.error(`  ✗ ${file} imports from ${from}, which is not there`);
      continue;
    }
    for (const name of names) {
      if (has.has(name)) continue;
      failed += 1;
      console.error(`  ✗ ${file} imports { ${name} } from ${from}, which does not export it`);
    }
  }
}

assert.ok(files.length > 10, "the walk found almost nothing, so it proves almost nothing");
if (failed) {
  console.error(`imports.test.mjs: ${failed} failed`);
  process.exit(1);
}
console.log(`imports.test.mjs: ok (${files.length} files)`);
