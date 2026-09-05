import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { targetIdentity, tripleOf } from "./shape.generated.js";

const cases = JSON.parse(readFileSync(new URL("../../fixtures/shape-identity.json", import.meta.url)));

test("the generated identity agrees with the shared fixture", () => {
  for (const c of cases) assert.equal(targetIdentity(c.target, c.kind), c.identity, c.name);
});

test("a triple carries the system the caller names", () => {
  assert.deepEqual(
    tripleOf({ system: "https://h", target: cases[0].target, kind: cases[0].kind }),
    ["https://h", cases[0].identity, cases[0].kind],
  );
});

test("a triple with no system named carries an empty one, never null", () => {
  const [system] = tripleOf({ system: null, target: cases[0].target, kind: cases[0].kind });
  assert.equal(system, "");
});
