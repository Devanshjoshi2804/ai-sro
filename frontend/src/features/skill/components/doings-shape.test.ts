import { describe, expect, it } from "vitest";
import {
  differs,
  fillOf,
  readingOf,
  shapeOf,
  shapesOf,
} from "@/features/skill/components/doings-shape";
import type { Demonstration } from "@/features/skill/api";

/**
 * Grouping demonstrations by how they were done.
 *
 * The rule under test everywhere here: the shape is *which* fields were filled,
 * never *what* was typed into them. Values differing is expected — it is what
 * makes a field a parameter — so folding values into the shape would give every
 * doing its own group and the grouping would do nothing at all.
 */
function doing(id: string, values: Record<string, string | null>): Demonstration {
  return {
    recording_id: id,
    started_at: "2026-08-27T09:00:00Z",
    demonstrator: "clerk@acme.test",
    frames: 4,
    diffed: false,
    values,
  } as Demonstration;
}

const names = ["work_area", "priority"];

describe("the shape of a doing", () => {
  it("is which fields were filled, not what was typed in them", () => {
    const one = doing("rec-1", { work_area: "SROTEST1", priority: "2" });
    const other = doing("rec-2", { work_area: "SROTEST2", priority: "9" });

    expect(shapeOf(one, names)).toBe(shapeOf(other, names));
  });

  it("separates a doing that left a field out from one that filled it", () => {
    const filled = doing("rec-1", { work_area: "SROTEST1", priority: "2" });
    const skipped = doing("rec-2", { work_area: "SROTEST2", priority: null });

    expect(shapeOf(filled, names)).not.toBe(shapeOf(skipped, names));
  });

  it("separates a doing that does not answer for a field from one that left it empty", () => {
    // Silence and emptiness are different evidence: one says the call did not
    // fit, the other says the warehouse accepted the field holding nothing.
    const silent = doing("rec-1", { work_area: "SROTEST1" });
    const empty = doing("rec-2", { work_area: "SROTEST2", priority: null });

    expect(fillOf(silent, "priority")).toBe("unread");
    expect(fillOf(empty, "priority")).toBe("empty");
    expect(shapeOf(silent, names)).not.toBe(shapeOf(empty, names));
  });
});

describe("grouping doings into shapes", () => {
  it("collapses doings that filled the same fields into one column", () => {
    const shapes = shapesOf(
      [
        doing("rec-1", { work_area: "A", priority: "1" }),
        doing("rec-2", { work_area: "B", priority: "2" }),
        doing("rec-3", { work_area: "C", priority: null }),
        doing("rec-4", { work_area: "D", priority: "4" }),
      ],
      names,
    );

    expect(shapes).toHaveLength(2);
    expect(shapes[0].doings.map((each) => each.recording_id)).toEqual(["rec-1", "rec-2", "rec-4"]);
    expect(shapes[1].doings.map((each) => each.recording_id)).toEqual(["rec-3"]);
  });

  it("keeps first-seen order so a one-off is not buried under a common shape", () => {
    // Ordering by how many doings share a shape would push the single unusual
    // demonstration to the end — and that is the one worth reading.
    const shapes = shapesOf(
      [
        doing("rec-1", { work_area: "A", priority: null }),
        doing("rec-2", { work_area: "B", priority: "2" }),
        doing("rec-3", { work_area: "C", priority: "3" }),
        doing("rec-4", { work_area: "D", priority: "4" }),
      ],
      names,
    );

    expect(shapes[0].doings).toHaveLength(1);
    expect(shapes[0].doings[0].recording_id).toBe("rec-1");
  });
});

describe("what a shape's column shows", () => {
  it("keeps every distinct value its doings used, in order", () => {
    const shape = {
      key: "ff",
      doings: [
        doing("rec-1", { work_area: "A" }),
        doing("rec-2", { work_area: "B" }),
        doing("rec-3", { work_area: "A" }),
      ],
    };

    expect(readingOf(shape, "work_area")).toEqual({ fill: "filled", values: ["A", "B"] });
  });

  it("says left empty rather than listing a value nobody sent", () => {
    const shape = { key: "e", doings: [doing("rec-1", { work_area: null })] };

    expect(readingOf(shape, "work_area")).toEqual({ fill: "empty", values: [] });
  });
});

describe("which rows are worth showing", () => {
  it("counts a field one doing left empty as differing", () => {
    const doings = [
      doing("rec-1", { work_area: "SG" }),
      doing("rec-2", { work_area: "SG" }),
      doing("rec-3", { work_area: null }),
    ];

    expect(differs(doings, "work_area")).toBe(true);
  });

  it("does not count a silent doing as a dissenting one", () => {
    // Otherwise one unreadable demonstration marks every row and the collapse
    // stops doing anything.
    const doings = [
      doing("rec-1", { work_area: "SG" }),
      doing("rec-2", { work_area: "SG" }),
      doing("rec-3", {}),
    ];

    expect(differs(doings, "work_area")).toBe(false);
  });

  it("does not call one answer agreement", () => {
    expect(differs([doing("rec-1", { work_area: "SG" }), doing("rec-2", {})], "work_area")).toBe(
      true,
    );
  });
});
