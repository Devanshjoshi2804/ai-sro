import { describe, expect, it } from "vitest";
import {
  became,
  money,
  outcomeLabel,
  spendLine,
  when,
  startOfToday,
} from "@/features/workflow/format";

describe("money", () => {
  it("says unpriced rather than inventing a free call", () => {
    expect(money({ cost_usd: 0, unpriced: true })).toBe("unpriced");
  });
  it("draws four decimals so a twentieth of a cent is visible", () => {
    expect(money({ cost_usd: 0.4708, unpriced: false })).toBe("$0.4708");
  });
  it("draws a real zero as zero, not as unpriced", () => {
    expect(money({ cost_usd: 0, unpriced: false })).toBe("$0.0000");
  });
});

describe("became", () => {
  it("says never run when nothing has", () => {
    expect(became({ total: 0, held: 0, stale: 0, earned: false })).toBe("never run");
  });
  it("does not pluralise a single run", () => {
    expect(became({ total: 1, held: 0, stale: 0, earned: false })).toBe("1 run · 0 held");
  });
  it("pluralises more than one", () => {
    expect(became({ total: 3, held: 2, stale: 0, earned: false })).toBe("3 runs · 2 held");
  });
  it("says writes unasked once the job has earned it", () => {
    expect(became({ total: 3, held: 2, stale: 0, earned: true })).toBe(
      "3 runs · 2 held · writes unasked",
    );
  });
  it("warns that the page is moving under the job", () => {
    expect(became({ total: 3, held: 2, stale: 1, earned: false })).toBe(
      "3 runs · 2 held · 1 step matched weakly",
    );
  });
  it("pluralises weakly-matched steps", () => {
    expect(became({ total: 3, held: 2, stale: 2, earned: false })).toBe(
      "3 runs · 2 held · 2 steps matched weakly",
    );
  });
});

describe("spendLine", () => {
  it("puts the day against its cap", () => {
    expect(spendLine({ cost_usd: 0.881104, unpriced: 0, cap_usd: 100 })).toEqual({
      text: "$0.8811 of $100.00 today",
      overCap: false,
    });
  });
  it("counts unpriced calls beside the total and never inside it", () => {
    expect(spendLine({ cost_usd: 0, unpriced: 3, cap_usd: 100 }).text).toBe(
      "$0.0000 of $100.00 today · 3 unpriced",
    );
  });
  it("omits the unpriced clause at zero rather than writing 0 unpriced", () => {
    expect(spendLine({ cost_usd: 1, unpriced: 0, cap_usd: 10 }).text).toBe(
      "$1.0000 of $10.00 today",
    );
  });
  it("is over cap at the cap, not past it — that is where the 429 starts", () => {
    expect(spendLine({ cost_usd: 10, unpriced: 0, cap_usd: 10 }).overCap).toBe(true);
  });
  it("an unpriced day stops the day just as hard as one over the cap", () => {
    expect(spendLine({ cost_usd: 0, unpriced: 1, cap_usd: 10 }).overCap).toBe(true);
  });
  it("a negative cap means no cap, and the day is not over it", () => {
    expect(spendLine({ cost_usd: 99, unpriced: 0, cap_usd: -1 })).toEqual({
      text: "$99.0000 spent today",
      overCap: false,
    });
  });
});

describe("when", () => {
  it("keeps the record in the rig's UTC and drops the T", () => {
    expect(when("2026-09-10T14:32:07.881104+00:00")).toBe("2026-09-10 14:32:07");
  });
  it("renders an absent time as nothing rather than the word null", () => {
    expect(when(null)).toBe("");
  });
});

describe("startOfToday", () => {
  it("is midnight in the reader's own zone, in the shape the input wants", () => {
    // Not toISOString().slice(0,16), which is UTC and wrong for anybody else.
    expect(startOfToday(new Date(2026, 8, 10, 17, 45))).toBe("2026-09-10T00:00");
  });
  it("pads a single-digit month and day", () => {
    expect(startOfToday(new Date(2026, 0, 5, 1, 2))).toBe("2026-01-05T00:00");
  });
});

describe("outcomeLabel", () => {
  it("marks a dry run, because a reader must never take one for a write", () => {
    expect(outcomeLabel({ outcome: "completed", live: false })).toBe("completed (dry)");
  });
  it("leaves a live run unmarked — the mark means the writes were withheld", () => {
    expect(outcomeLabel({ outcome: "completed", live: true })).toBe("completed");
  });
});
