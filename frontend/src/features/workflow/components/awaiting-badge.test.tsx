/**
 * The badge is an alarm, and an alarm that is always on is not one. The harm it
 * can do is sit at `0` until nobody reads it any more, or stay silent while a
 * browser holds a warehouse write open.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithQuery } from "@/test/render";
import { AwaitingBadge } from "@/features/workflow/components/awaiting-badge";
import * as workflowApi from "@/features/workflow/api";

const parked = {
  id: "wrun_a",
  tenant: "acme",
  workflow_id: "wfl_1",
  device_id: "dev_a",
  values: {},
  started_by: "devansh",
  live: true,
  allow_focus: true,
  started_at: "2026-09-10T10:00:00+00:00",
  finished_at: null,
  outcome: "running",
  from_step: 0,
  withheld: [],
  in_tokens: 0,
  out_tokens: 0,
  thought_tokens: 0,
  cost_usd: 0,
  unpriced: false,
  steps: [
    {
      order: 1,
      says: "Save the new work area",
      verdict: "awaiting",
      verdict_by: "",
      reason: "",
      planned_by: "model",
      sent: { method: "POST", url: "/save" },
      result: null,
      matched_by: null,
      stale: false,
      before_url: null,
      after_url: null,
      in_tokens: 0,
      out_tokens: 0,
      thought_tokens: 0,
      cost_usd: 0,
      unpriced: false,
    },
  ],
};

describe("AwaitingBadge", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders nothing at all when nothing is waiting", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns").mockResolvedValue([] as never);
    const { container } = renderWithQuery(<AwaitingBadge />);
    // The query has to be allowed to land: rendering nothing while loading is
    // not the same claim as rendering nothing once the answer is in.
    await new Promise((r) => setTimeout(r, 0));
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the count when a browser is holding a write open", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns")
      .mockResolvedValue([parked, { ...parked, id: "wrun_b" }] as never);
    renderWithQuery(<AwaitingBadge />);
    expect(await screen.findByText("2")).toBeInTheDocument();
  });
});
