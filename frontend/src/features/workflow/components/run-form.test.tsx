/**
 * This is the button that makes a real Chrome do real work in a warehouse.
 * The harm it can do is send a write nobody asked for, or start a run and
 * then lose it.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { RunForm } from "@/features/workflow/components/run-form";
import * as workflowApi from "@/features/workflow/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const workflow = {
  id: "wfl_1",
  title: "Create a Work Area",
  narrative: "",
  systems: [],
  pass_id: "p",
  steps: [],
  runs: { total: 0, held: 0, stale: 0, earned: false },
  parameters: [{ name: "workArea", seen_values: ["Three TE", "NEWTESTS", "twoTEST"] }],
};

const browser = {
  device_id: "dev_a",
  principal_id: "devansh",
  label: "Macintosh · Chrome",
  registered_at: "2026-08-26T05:56:55+00:00",
  last_seen_at: "2026-09-10T10:28:28+00:00",
  revoked_at: null,
  online: true,
};

describe("RunForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    push.mockClear();
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([browser] as never);
  });

  it("prefills the last value a recording actually carried", async () => {
    renderWithQuery(<RunForm workflow={workflow as never} />);
    expect(await screen.findByLabelText("workArea")).toHaveValue("twoTEST");
  });

  it("is dry unless a person ticks it", async () => {
    const start = vi
      .spyOn(workflowApi, "startWorkflowRun")
      .mockResolvedValue({ id: "wrun_a" } as never);
    renderWithQuery(<RunForm workflow={workflow as never} />);
    await userEvent.click(await screen.findByRole("button", { name: /start/i }));
    await waitFor(() => expect(start).toHaveBeenCalled());
    expect(start.mock.calls[0][0].live).toBe(false);
  });

  it("sends the writes only when the box is ticked", async () => {
    const start = vi
      .spyOn(workflowApi, "startWorkflowRun")
      .mockResolvedValue({ id: "wrun_a" } as never);
    renderWithQuery(<RunForm workflow={workflow as never} />);
    await screen.findByLabelText("workArea");
    await userEvent.click(screen.getByLabelText(/live — send the writes/i));
    await userEvent.click(screen.getByRole("button", { name: /start/i }));
    await waitFor(() => expect(start.mock.calls[0][0].live).toBe(true));
  });

  it("refuses three spaces the way the route refuses a blank", async () => {
    const start = vi.spyOn(workflowApi, "startWorkflowRun").mockResolvedValue({} as never);
    renderWithQuery(<RunForm workflow={workflow as never} />);
    const field = await screen.findByLabelText("workArea");
    await userEvent.clear(field);
    await userEvent.type(field, "   ");
    await userEvent.click(screen.getByRole("button", { name: /start/i }));
    expect(await screen.findByText("this job needs a value for: workArea")).toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
  });

  it("trims a value pasted with a trailing space", async () => {
    const start = vi
      .spyOn(workflowApi, "startWorkflowRun")
      .mockResolvedValue({ id: "wrun_a" } as never);
    renderWithQuery(<RunForm workflow={workflow as never} />);
    const field = await screen.findByLabelText("workArea");
    await userEvent.clear(field);
    await userEvent.type(field, "ZONE-7 ");
    await userEvent.click(screen.getByRole("button", { name: /start/i }));
    await waitFor(() => expect(start.mock.calls[0][0].values).toEqual({ workArea: "ZONE-7" }));
  });

  it("cannot start a run when no browser could drive it", async () => {
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([] as never);
    renderWithQuery(<RunForm workflow={workflow as never} />);
    expect(await screen.findByText(/no browser is connected/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start/i })).toBeDisabled();
  });

  it("will not offer a revoked browser as one that could drive a run", async () => {
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([
      { ...browser, revoked_at: "2026-09-01T00:00:00+00:00" },
    ] as never);
    renderWithQuery(<RunForm workflow={workflow as never} />);
    expect(await screen.findByText(/no browser is connected/i)).toBeInTheDocument();
  });

  it("follows the started run by its id — not by a field that does not exist", async () => {
    vi.spyOn(workflowApi, "startWorkflowRun").mockResolvedValue({ id: "wrun_a" } as never);
    renderWithQuery(<RunForm workflow={workflow as never} />);
    await userEvent.click(await screen.findByRole("button", { name: /start/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/jobs/runs/wrun_a"));
  });

  it("says why the route refused rather than looking like it worked", async () => {
    vi.spyOn(workflowApi, "startWorkflowRun").mockRejectedValue(
      new Error("that browser is already driving a run"),
    );
    renderWithQuery(<RunForm workflow={workflow as never} />);
    await userEvent.click(await screen.findByRole("button", { name: /start/i }));
    expect(await screen.findByText(/that browser is already driving a run/)).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
