/**
 * The audit is what a person points at when asked who let a warehouse write
 * out. The harm it can do is show a time that is not the time in the record.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { AuditWalk } from "@/features/workflow/components/audit-walk";
import * as workflowApi from "@/features/workflow/api";

const empty = { since: "2026-09-10T00:00:00+00:00", runs: [], offers: [], devices: [], chats: [] };

describe("AuditWalk", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([
      {
        id: "wfl_1",
        title: "Create a Work Area",
        narrative: "",
        systems: [],
        pass_id: "p",
        parameters: [],
        unproven: [],
        steps: [],
        runs: { total: 0, held: 0, stale: 0, earned: false },
      },
    ] as never);
  });

  it("always sends a since, because the door refuses a request without one", async () => {
    const read = vi.spyOn(workflowApi, "readAudit").mockResolvedValue(empty as never);
    renderWithQuery(<AuditWalk />);
    await screen.findByText(/browsers/i);
    expect(read).toHaveBeenCalled();
    expect(read.mock.calls[0][0]).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("keeps a row in the record's own UTC", async () => {
    vi.spyOn(workflowApi, "readAudit").mockResolvedValue({
      ...empty,
      devices: [
        { device_id: "dev_a", registered_at: "2026-09-10T14:32:07+00:00", revoked_at: null },
      ],
    } as never);
    renderWithQuery(<AuditWalk />);
    expect(await screen.findByText(/2026-09-10 14:32:07/)).toBeInTheDocument();
  });

  it("names who let a write out, and says so plainly when nobody was named", async () => {
    vi.spyOn(workflowApi, "readAudit").mockResolvedValue({
      ...empty,
      runs: [
        {
          id: "wrun_a",
          workflow_id: "wfl_1",
          device_id: "dev_a",
          started_by: "devansh",
          live: true,
          started_at: "2026-09-10T10:00:00+00:00",
          finished_at: null,
          outcome: "completed",
          cost_usd: 0.5,
          unpriced: false,
          steps: [
            {
              order: 1,
              says: "Save",
              verdict: "held",
              verdict_by: "state",
              reason: "",
              sent: null,
              matched_by: null,
              stale: false,
              approved_at: "2026-09-10T10:01:00+00:00",
              approved_by: null,
            },
          ],
        },
      ],
    } as never);
    renderWithQuery(<AuditWalk />);
    expect(
      await screen.findByText(/approved 2026-09-10 10:01:00 by the tenant/),
    ).toBeInTheDocument();
  });

  it("marks a dry run as dry so nobody reads it as a write", async () => {
    vi.spyOn(workflowApi, "readAudit").mockResolvedValue({
      ...empty,
      runs: [
        {
          id: "wrun_a",
          workflow_id: "wfl_1",
          device_id: "dev_a",
          started_by: "devansh",
          live: false,
          started_at: "2026-09-10T10:00:00+00:00",
          finished_at: null,
          outcome: "completed",
          cost_usd: 0,
          unpriced: false,
          steps: [],
        },
      ],
    } as never);
    renderWithQuery(<AuditWalk />);
    expect(await screen.findByText(/completed \(dry\)/)).toBeInTheDocument();
  });

  it("says none for a section with nothing in it, rather than hiding it", async () => {
    vi.spyOn(workflowApi, "readAudit").mockResolvedValue(empty as never);
    renderWithQuery(<AuditWalk />);
    expect(await screen.findAllByText("none")).toHaveLength(4);
  });

  it("re-reads when the reader moves the since", async () => {
    const read = vi.spyOn(workflowApi, "readAudit").mockResolvedValue(empty as never);
    renderWithQuery(<AuditWalk />);
    await screen.findAllByText("none");
    const field = screen.getByLabelText(/since/i);
    await userEvent.clear(field);
    await userEvent.type(field, "2026-09-01T00:00");
    await screen.findAllByText("none");
    expect(read.mock.calls.length).toBeGreaterThan(1);
  });
});
