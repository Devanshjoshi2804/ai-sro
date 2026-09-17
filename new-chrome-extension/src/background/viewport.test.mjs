// Self-check for `viewportInPage`: the digest that goes beside the picture.
//
// It runs inside the page and it runs on a warehouse grid, which is the whole
// difficulty. `getBoundingClientRect` forces layout, and this used to call it
// on every match of a selector including `.x-grid-cell` -- then keep 200 of
// the answers and throw the rest away. Measured on the deployment, 2026-09-17
// at 17:30: `run_0c3bd2ae` step 2 failed `no screen to look at: timeout: the
// browser did not answer within 20s`, and the same timeout had been read as
// three different faults across the afternoon.
//
// Run with `node src/background/viewport.test.mjs`.

import assert from "node:assert/strict";
import test from "node:test";

/** One element, counting every time its geometry is asked for. That count is
 * the thing under test: it is what costs the time on a real grid. */
function cell(name, box, measured) {
  return {
    getBoundingClientRect() {
      measured.count += 1;
      return box;
    },
    getAttribute: () => null,
    textContent: name,
    name: "",
  };
}

const box = (top, height = 20) => ({
  x: 10,
  y: top,
  top,
  bottom: top + height,
  left: 10,
  right: 110,
  width: 100,
  height,
});

function page(elements) {
  globalThis.window = { innerWidth: 1000, innerHeight: 800 };
  globalThis.location = { href: "https://wms.example/portal" };
  globalThis.document = { querySelectorAll: () => elements };
}

const { viewportInPage } = await import("./in-page.js");

test("a grid with fifty thousand cells is not measured fifty thousand times", () => {
  // The fault itself. Nothing here asserts a duration -- a timing assertion in
  // a unit test is a flake waiting for a slow machine -- so it counts the
  // calls that cost the duration instead.
  // Off the screen, every one of them, which is what a scrolled grid mostly
  // is. That matters: an on-screen grid stops the loop at the two hundredth
  // NAME, so the answer cap hides the missing work cap. Nothing names these,
  // so only a bound on the work itself can stop this.
  const measured = { count: 0 };
  const many = Array.from({ length: 50_000 }, (_, n) =>
    cell(`cell ${n}`, box(2000 + n * 20), measured),
  );
  page(many);

  viewportInPage();

  assert.ok(measured.count <= 2000, `it measured ${measured.count} elements`);
});

test("it stops once it has enough to say, rather than measuring everything first", () => {
  // Two limits and they are different limits: one bounds the work, one bounds
  // the answer. Only the second existed before, which is why the work was
  // unbounded.
  const measured = { count: 0 };
  page(Array.from({ length: 2000 }, (_, n) => cell(`row ${n}`, box(10), measured)));

  const seen = viewportInPage();

  assert.equal(seen.digest.split("\n").length, 200);
  assert.ok(measured.count <= 220, `it measured ${measured.count} to name 200`);
});

test("what is off the screen is not described as being on it", () => {
  // The coordinates beside each name are thousandths of the viewport, so a row
  // scrolled a thousand pixels below the fold was being written down at
  // `y: 4300` in a space that ends at 1000. Wrong as well as slow.
  const measured = { count: 0 };
  page([
    cell("Visible", box(100), measured),
    cell("Far below", box(4000), measured),
    cell("Above", box(-500), measured),
  ]);

  const seen = viewportInPage();

  assert.match(seen.digest, /Visible/);
  assert.doesNotMatch(seen.digest, /Far below|Above/);
  for (const line of seen.digest.split("\n")) {
    const [, y] = line.split(": ")[1].split(",");
    assert.ok(Number(y) >= 0 && Number(y) <= 1000, line);
  }
});

test("a control too small to press is not a control", () => {
  const measured = { count: 0 };
  page([cell("Real", box(100), measured), cell("Hairline", box(100, 1), measured)]);

  assert.equal(viewportInPage().digest, "Real: 60,138");
});

test("it still says where the browser is and how big the screen is", () => {
  page([]);
  const seen = viewportInPage();
  assert.equal(seen.url, "https://wms.example/portal");
  assert.equal(seen.width, 1000);
  assert.equal(seen.height, 800);
  assert.equal(seen.digest, "");
});
