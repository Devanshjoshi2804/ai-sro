/**
 * A dry run's whole worth is the writes it did not send. The harm this screen
 * can do is draw an empty box where one of those writes should be, or offer a
 * press that sends one on a run that is past taking it.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithQuery } from "@/test/render";
import { WorkflowRunDetail } from "@/features/workflow/components/workflow-run-detail";
import * as workflowApi from "@/features/workflow/api";

const step = (over: Partial<workflowApi.WorkflowRunStepModel> = {}) => ({
  order: 0,
  // Where in the run, which step of the job, and which thing on the list --
  // the last two being the same step and no list at all for a job that does
  // one thing once.
  of_step: 0,
  item: null,
  // Nothing created: what a run made is what a person goes and looks at, and
  // most steps make nothing.
  made: {},
  says: "open the order",
  verdict: "held",
  verdict_by: "",
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
  cost_usd: 0.0012,
  unpriced: false,
  ...over,
});

const run = (over: Partial<workflowApi.WorkflowRunModel> = {}) => ({
  id: "run_1",
  tenant: "greyorange",
  workflow_id: "wf_1",
  device_id: "dev_a",
  values: {},
  started_by: "devansh",
  live: false,
  allow_focus: true,
  started_at: "2026-09-10T10:28:28+00:00",
  finished_at: null,
  outcome: "running",
  from_step: 0,
  items: [],
  steps: [step()],
  withheld: [],
  in_tokens: 10,
  out_tokens: 20,
  thought_tokens: 0,
  cost_usd: 0.0345,
  unpriced: false,
  ...over,
});

const show = (over: Partial<workflowApi.WorkflowRunModel> = {}) => {
  vi.spyOn(workflowApi, "getWorkflowRun").mockResolvedValue(run(over) as never);
  return renderWithQuery(<WorkflowRunDetail runId="run_1" />);
};

describe("WorkflowRunDetail", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("offers Approve on a parked run", async () => {
    show({ steps: [step({ verdict: "awaiting" })] });
    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
  });

  it("does not offer Approve on a running run with nothing awaiting", async () => {
    show({ steps: [step({ verdict: "held" })] });
    expect(await screen.findByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
  });

  it("offers neither Approve nor Stop on a finished run", async () => {
    show({
      outcome: "held",
      finished_at: "2026-09-10T10:31:02+00:00",
      // Awaiting on a run that is over is a leftover, not an invitation.
      steps: [step({ verdict: "awaiting" })],
    });
    expect(await screen.findByText(/held \(dry\)/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
  });

  it("says unpriced rather than inventing a bill of $0.0000", async () => {
    show({ cost_usd: 0, unpriced: true });
    expect(await screen.findByText("unpriced")).toBeInTheDocument();
    expect(screen.queryByText("$0.0000")).toBeNull();
  });

  it("prints planned for a withheld write with no recorded call", async () => {
    show({
      outcome: "held",
      finished_at: "2026-09-10T10:31:02+00:00",
      withheld: [{ step: 2, planned: { kind: "http", payload: { sku: "SKU-9" } } }],
    });
    const box = await screen.findByText(/"kind": "http"/);
    expect(box.textContent).toContain("step 2");
    expect(box.textContent).toContain('"sku": "SKU-9"');
  });

  it("still prints planned when a call was recorded", async () => {
    show({
      outcome: "held",
      withheld: [
        {
          step: 1,
          method: "POST",
          url: "https://wms.example/api/orders",
          body: '{"id":7}',
          planned: { kind: "http", payload: { id: 7 } },
        },
      ],
    });
    const box = await screen.findByText(/wms\.example/);
    expect(box.textContent).toContain("POST https://wms.example/api/orders");
    expect(box.textContent).toContain('{"id":7}');
    expect(box.textContent).toContain('"kind": "http"');
  });

  it("draws no withheld heading when nothing was withheld", async () => {
    show({ outcome: "held", withheld: [] });
    expect(await screen.findByText(/held \(dry\)/)).toBeInTheDocument();
    expect(screen.queryByText("what a live run would have sent")).toBeNull();
  });

  it("tells a failed step from a held one", async () => {
    const { container } = show({
      outcome: "failed",
      steps: [
        step({ order: 0, verdict: "held" }),
        step({ order: 1, says: "confirm", verdict: "failed", reason: "the page never loaded" }),
      ],
    });
    expect(await screen.findByText("confirm")).toBeInTheDocument();
    const held = container.querySelector('[data-verdict="held"]');
    const failed = container.querySelector('[data-verdict="failed"]');
    expect(held).not.toBeNull();
    expect(failed).not.toBeNull();
    expect(held?.className).not.toEqual(failed?.className);
    expect(screen.getByText("the page never loaded")).toBeInTheDocument();
  });

  it("says what refused rather than a blank screen", async () => {
    vi.spyOn(workflowApi, "getWorkflowRun").mockRejectedValue(new Error("no such run"));
    renderWithQuery(<WorkflowRunDetail runId="run_1" />);
    expect(await screen.findByText(/no such run/)).toBeInTheDocument();
  });
});
