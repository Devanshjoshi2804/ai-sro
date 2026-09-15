/**
 * A parked run is a live browser holding a warehouse write open, waiting.
 * The harm this screen can do is let a person approve without seeing what
 * they are approving, or show a run as parked when nothing is waiting.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { NeedsAPerson } from "@/features/workflow/components/needs-a-person";
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
  cost_usd: 0.12,
  unpriced: false,
  steps: [
    {
      order: 1,
      says: "Open the work area tab",
      verdict: "held",
      verdict_by: "state",
      reason: "",
      planned_by: null,
      sent: null,
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
    {
      order: 2,
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

const workflows = [
  {
    id: "wfl_1",
    title: "Create a Work Area",
    narrative: "",
    systems: [],
    pass_id: "p1",
    parameters: [],
    steps: [],
    runs: { total: 0, held: 0, stale: 0, earned: false },
  },
];

describe("NeedsAPerson", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue(workflows as never);
  });

  it("names the job rather than only its id", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns").mockResolvedValue([parked] as never);
    renderWithQuery(<NeedsAPerson />);
    expect(await screen.findByText("Create a Work Area")).toBeInTheDocument();
  });

  it("shows the write a person is being asked to let out", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns").mockResolvedValue([parked] as never);
    renderWithQuery(<NeedsAPerson />);
    expect(await screen.findByText(/Save the new work area/)).toBeInTheDocument();
    expect(screen.getByText(/"\/save"/)).toBeInTheDocument();
  });

  it("approves the run a bare tap approves — no body, no device", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns").mockResolvedValue([parked] as never);
    const approve = vi
      .spyOn(workflowApi, "approveWorkflowRun")
      .mockResolvedValue({ order: 2, first: true } as never);
    renderWithQuery(<NeedsAPerson />);
    await userEvent.click(await screen.findByRole("button", { name: /approve/i }));
    await waitFor(() => expect(approve).toHaveBeenCalledWith("wrun_a"));
  });

  it("does not show a run whose wait already ran out as still waiting", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns").mockResolvedValue([
      { ...parked, outcome: "failed" },
    ] as never);
    renderWithQuery(<NeedsAPerson />);
    expect(await screen.findByText(/nothing is waiting on a person/i)).toBeInTheDocument();
  });

  it("says why an approval was refused rather than going quiet", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns").mockResolvedValue([parked] as never);
    vi.spyOn(workflowApi, "approveWorkflowRun").mockRejectedValue(
      new Error("nothing is awaiting approval on this run"),
    );
    renderWithQuery(<NeedsAPerson />);
    await userEvent.click(await screen.findByRole("button", { name: /approve/i }));
    expect(await screen.findByText(/nothing is awaiting approval on this run/)).toBeInTheDocument();
  });

  it("stops a run from here too", async () => {
    vi.spyOn(workflowApi, "listAwaitingRuns").mockResolvedValue([parked] as never);
    const abort = vi.spyOn(workflowApi, "abortWorkflowRun").mockResolvedValue({} as never);
    renderWithQuery(<NeedsAPerson />);
    await userEvent.click(await screen.findByRole("button", { name: /^stop$/i }));
    await waitFor(() => expect(abort).toHaveBeenCalledWith("wrun_a"));
  });
});
