import { describe, expect, it } from "vitest";
import { offersToExplore } from "@/features/console/pursuit-card";

// The explore card offers to drive the warehouse's screens. It belongs under
// one reply only: "nothing has been taught for that", which the backend marks
// `pursuable`. Under a status line ("check now") it was an offer to explore
// something nobody had asked for (F2).
describe("offersToExplore", () => {
  it("offers only under the nothing-taught reply", () => {
    expect(offersToExplore({ matched_skill_id: null, pursuable: true })).toBe(true);
  });

  it.each([
    ["a status line", {}],
    ["an offer", { kind: "job", workflow_id: "wfl_1", title: "Create" }],
    ["a question for values", { kind: "needs_values", workflow_id: "wfl_1", missing: ["Code"] }],
    ["a run asking", { kind: "run_asks", run_id: "run_1", question_id: "q_1" }],
    ["a matched skill", { matched_skill_id: "skill-adjust", pursuable: false }],
    ["which did you mean", { kind: "which_job", choices: ["wfl_1", "wfl_2"] }],
    ["a resolver decision with no match", { matched_skill_id: null, choices: [] }],
    ["nothing at all", undefined],
  ])("does not offer under %s", (_name, decision) => {
    expect(offersToExplore(decision)).toBe(false);
  });
});
