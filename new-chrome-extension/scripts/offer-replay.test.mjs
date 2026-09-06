// The replay's own arithmetic, on a corpus small enough to see: the counts
// the summary line carries have to be the counts a person would reach by
// reading the table.
import assert from "node:assert/strict";
import test from "node:test";
import { replay, tally } from "./offer-replay.mjs";

const H = "https://wms.example";
const t = (id, kind = "type") => [H, id, kind];
const g = (id, kind = "type", at = 1) => ({ triple: t(id, kind), value: null, secret: false, at });
const shapes = [
  { id: "wfl_a", title: "A", held_runs: 0, shape: [t("a1"), t("a2"), t("save", "click")], parameters: [] },
  { id: "wfl_b", title: "B", held_runs: 0, shape: [t("b1"), t("shared"), t("save", "click")], parameters: [] },
  { id: "wfl_c", title: "C", held_runs: 0, shape: [t("b1"), t("shared"), t("c3"), t("save", "click")], parameters: [] },
];
const jobs = [
  { id: "wfl_a", title: "A", gestures: [g("a1"), g("a2"), g("save", "click")] },
  // B and C share their first two gestures; C is told apart on its third.
  { id: "wfl_c", title: "C", gestures: [g("b1"), g("shared"), g("c3"), g("save", "click")] },
  // A job whose gestures match nothing served.
  { id: "wfl_x", title: "X", gestures: [g("x1"), g("x2")] },
  // A job offered as another: its first two gestures are A's.
  { id: "wfl_d", title: "D", gestures: [g("a1"), g("a2"), g("d3")] },
];

test("each job is offered at the first gesture that names one job, or never", () => {
  const rows = replay(shapes, jobs);
  assert.deepEqual(
    rows.map((r) => [r.job.id, r.offered && [r.offered.at, r.offered.k, r.offered.workflowId]]),
    [
      ["wfl_a", [2, 2, "wfl_a"]],
      ["wfl_c", [3, 3, "wfl_c"]],
      ["wfl_x", null],
      ["wfl_d", [2, 2, "wfl_a"]],
    ],
  );
});

test("the summary counts are the table read by a person", () => {
  assert.deepEqual(tally(replay(shapes, jobs)), { right: 2, wrong: 1, never: 1 });
});
