// Self-check for the systems that are watched wherever they open.
//
// Run with `node src/background/always.test.mjs`.

import assert from "node:assert";
import { test } from "node:test";

const { alsoWatch, alwaysWatched, hostOf } = await import("./always.js");

test("a system said once is watched on every tab of it", () => {
  // The defect this exists for: a run drove a tab it had opened itself while
  // the panel said "not watched", so nothing it did was evidence.
  const hosts = alsoWatch("wms.example", []);
  assert.ok(alwaysWatched("https://wms.example/portal?siteId=SG#anything", hosts));
  assert.ok(alwaysWatched("https://wms.example/other/page", hosts));
  assert.ok(!alwaysWatched("https://mail.example/inbox", hosts));
});

test("only pages, and only the name the browser shows", () => {
  const hosts = alsoWatch("wms.example", []);
  assert.equal(hostOf("chrome://settings"), "");
  assert.equal(hostOf("not a url"), "");
  assert.ok(!alwaysWatched("chrome://settings", hosts));
  // Not a pattern language: a second matcher to keep in step with the
  // tenant policy's own is a second matcher to get wrong.
  assert.ok(!alwaysWatched("https://evil.wms.example/portal", hosts));
});

test("saying it twice says it once", () => {
  assert.deepEqual(alsoWatch("wms.example", ["wms.example"]), ["wms.example"]);
  assert.deepEqual(alsoWatch("a.example", ["b.example"]), ["a.example", "b.example"]);
});
