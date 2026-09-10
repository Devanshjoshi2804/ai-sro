/**
 * The board an operator reads before pressing anything. What it can get wrong
 * is quieter than the run form's harm but not smaller: a step whose system is
 * unknown drawn as if it were known, or a pass id drawn as a price — one
 * mining call proposes every job in a pass, so a per-card dollar figure would
 * bill the whole pass once per card.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { JobBoard } from "@/features/workflow/components/job-board";
import * as workflowApi from "@/features/workflow/api";

const workflow = {
  id: "wfl_1",
  title: "Create a Work Area",
  narrative: "An operator opens the work areas grid and adds one.",
  systems: ["blue-yonder", "sap"],
  pass_id: "pass_7f2",
  unproven: [],
  parameters: [{ name: "workArea", seen_values: ["Three TE", "twoTEST"] }],
  steps: [
    { order: 1, says: "Open the work areas grid", system: "blue-yonder", cites: ["c1"], parameters: [] },
    { order: 2, says: "Type the work area name", system: null, cites: [], parameters: ["workArea"] },
  ],
  runs: { total: 2, held: 1, stale: 0, earned: false },
};

const run = {
  id: "wrun_a",
  started_at: "2026-09-10T10:28:28+00:00",
  started_by: "devansh",
  outcome: "succeeded",
  live: true,
};

describe("JobBoard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(workflowApi, "listRunsOfWorkflow").mockResolvedValue([] as never);
  });

  it("says what the job is, where it runs and what it reads from", async () => {
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([workflow] as never);
    renderWithQuery(<JobBoard />);
    expect(await screen.findByText("Create a Work Area")).toBeInTheDocument();
    expect(screen.getByText(workflow.narrative)).toBeInTheDocument();
    // Two spaces, not one: the default normaliser would collapse them.
    expect(screen.getByText("blue-yonder  sap", { normalizer: (t) => t })).toBeInTheDocument();
  });

  it("says what has become of the job", async () => {
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([workflow] as never);
    renderWithQuery(<JobBoard />);
    expect(await screen.findByText("2 runs · 1 held")).toBeInTheDocument();
  });

  it("does not pretend to know the system of a step that never said", async () => {
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([workflow] as never);
    renderWithQuery(<JobBoard />);
    expect(await screen.findByText("system unknown · 0 cited")).toBeInTheDocument();
    // No pluralisation, as the rig had it.
    expect(screen.getByText("blue-yonder · 1 cited")).toBeInTheDocument();
  });

  it("draws the pass id as an id and not as a price", async () => {
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([workflow] as never);
    renderWithQuery(<JobBoard />);
    const passId = await screen.findByText("pass_7f2");
    const card = passId.closest("[data-slot=card]");
    expect(card).not.toBeNull();
    expect(card!.textContent).not.toContain("$");
  });

  it("says nothing has been mined rather than showing an empty board", async () => {
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([] as never);
    renderWithQuery(<JobBoard />);
    expect(await screen.findByText("Nothing has been mined yet.")).toBeInTheDocument();
  });

  it("shows the recent runs of a job when asked for them", async () => {
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([workflow] as never);
    vi.spyOn(workflowApi, "listRunsOfWorkflow").mockResolvedValue([run] as never);
    renderWithQuery(<JobBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "past runs" }));
    expect(await screen.findByText("2026-09-10 10:28:28")).toBeInTheDocument();
    expect(screen.getByText("succeeded")).toBeInTheDocument();
    expect(screen.getByText("by devansh")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "open" })).toHaveAttribute(
      "href",
      "/jobs/runs/wrun_a",
    );
  });

  it("says a job has no runs rather than showing an empty list", async () => {
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([workflow] as never);
    renderWithQuery(<JobBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "past runs" }));
    expect(await screen.findByText("no runs yet")).toBeInTheDocument();
  });
});
