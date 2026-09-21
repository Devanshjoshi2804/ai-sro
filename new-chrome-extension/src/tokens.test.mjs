/**
 * The palette this extension paints with, against the one the console paints
 * with.
 *
 * A generated file that is only checked somewhere else is a generated file that
 * drifts -- which is how the panel came to ship `#e8621f` while the console
 * shipped `#F47B20` and neither was the brand. This asks the question here, and
 * says what to run.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");

const source = readFileSync(join(root, "frontend", "src", "app", "brand.css"), "utf8");
const copy = readFileSync(join(here, "brand.generated.css"), "utf8");

assert.ok(
  copy.endsWith(source),
  "new-chrome-extension/src/brand.generated.css is out of date. Run: make tokens",
);

// The one value the whole exercise exists to keep singular. Declarations only:
// the file's own comment names the two wrong oranges, which is the point of it.
const declarations = copy.replace(/\/\*[\s\S]*?\*\//g, "");
assert.match(source, /--brand-accent:\s*#dc582a;/i, "the brand accent moved without this test");
assert.ok(
  !/#e8621f|#f47b20/i.test(declarations),
  "an orange that is not the brand's is back in the extension",
);

console.log("tokens.test.mjs ok");


// Every token the panel paints with, against the ones that exist.
//
// A `var(--text)` nobody defines is not an error anywhere: CSS drops the
// declaration and the element inherits whatever was above it, so the colour is
// nearly right and nothing says otherwise. Written the day the panel's own
// tabs, the waiting count and the result card all shipped with `--text` and
// `--muted`, which this palette has never had -- it calls them `--ink` and
// `--ink-mute`.
//
// A fallback is a decision rather than a mistake: `var(--font-body, system-ui)`
// says what to do without one, so it is left alone.

const panel = readFileSync(join(here, "panel", "panel.css"), "utf8");
const defined = new Set([
  ...panel.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm),
  ...copy.matchAll(/^\s*(--[a-z0-9-]+)\s*:/gm),
].map(([, name]) => name));
const undefinedTokens = [
  ...new Set(
    [...panel.matchAll(/var\((--[a-z0-9-]+)\s*(,?)/g)]
      .filter(([, , comma]) => !comma)
      .map(([, name]) => name)
      .filter((name) => !defined.has(name)),
  ),
].sort();

assert.deepEqual(
  undefinedTokens,
  [],
  `panel.css paints with tokens nothing defines: ${undefinedTokens.join(", ")}`,
);
