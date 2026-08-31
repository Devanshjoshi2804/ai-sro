import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { SkillDoings } from "@/features/skill/components/skill-doings";
import * as skills from "@/features/skill/api";
import * as recordings from "@/features/recording/api";

/**
 * A task demonstrated many times keeps every doing, and this is where a
 * reviewer reads them. Three different facts share this table and must not be
 * shown as each other: a value, a field sent holding nothing, and a field this
 * doing does not answer for. A cell nobody measured, rendered as a value, is
 * indistinguishable from a measurement.
 */
const parameterShape = {
  name: "work_area",
  kind: "input",
  description: "",
  observed_values: [],
  source_step_index: null,
  options: null,
  optional: false,
  absent_as: null,
  evidence: "proven",
};

const parameter = parameterShape;

const constant = { ...parameterShape, name: "facility" };

const version = {
  version: 1,
  stage: "recorded",
  summary: "",
  when_to_use: "",
  track_record: {
    clean_streak: 0,
    consecutive_failures: 0,
    clean_runs: 0,
    degraded_runs: 0,
    failed_runs: 0,
    unreachable_runs: 0,
  },
  ready_for_autonomy: null,
  demotion_reason: null,
  induced_at: "2026-03-01T09:00:00Z",
  induced_by: "clerk@acme.test",
  recording_ids: ["rec-1", "rec-2", "rec-3", "rec-4"],
  repaired_from: null,
  provenance_note: "",
  steps: [],
  parameters: [parameter, constant],
  loops: [],
  systems: [],
};

function doing(id: string, values: Record<string, string | null>, diffed = false) {
  return {
    recording_id: id,
    started_at: "2026-03-01T09:00:00Z",
    demonstrator: "clerk@acme.test",
    frames: 4,
    diffed,
    values,
  };
}

// Four doings, three shapes: the first two filled the same fields (different
// values), the third left one out, the fourth answers for nothing.
const four = [
  doing("rec-1", { work_area: "FOURTH", facility: "SG" }, true),
  doing("rec-2", { work_area: "THIRD", facility: "SG" }, true),
  doing("rec-3", { work_area: null, facility: "SG" }),
  // Answers for no field at all: its calls do not fit what this version sends.
  doing("rec-4", {}),
];

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(skills, "getDoings").mockResolvedValue(four as never);
  vi.spyOn(recordings, "getMedia").mockResolvedValue([]);
  vi.spyOn(recordings, "getRecording").mockResolvedValue({
    id: "rec-1",
    frames: [],
    artifacts: [],
    started_at: "2026-03-01T09:00:00Z",
    demonstrator: "clerk@acme.test",
  } as never);
});

describe("the doings behind a skill", () => {
  it("gives a column to each distinct way the task was done, not to each doing", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    // Four doings, three shapes: rec-1 and rec-2 filled the same fields and
    // only their values differ, which is not a different way of doing the job.
    await waitFor(() => expect(screen.getByText("FOURTH")).toBeInTheDocument());
    expect(screen.getAllByRole("columnheader")).toHaveLength(4);
    expect(screen.getByText("2 doings")).toBeInTheDocument();
    expect(screen.getByText(/3 distinct ways/i)).toBeInTheDocument();
  });

  it("keeps every value a shared column covered, reachable", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    // The column shows one value and says there is another behind it, rather
    // than picking one and silently dropping the rest.
    await waitFor(() => expect(screen.getByText("FOURTH")).toBeInTheDocument());
    expect(screen.queryByText("THIRD")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "+1" }));
    await waitFor(() => expect(screen.getByText("THIRD")).toBeInTheDocument());
  });

  it("can be asked for one column per doing instead", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    await waitFor(() => expect(screen.getByText("FOURTH")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /show every doing/i }));

    await waitFor(() => expect(screen.getAllByRole("columnheader")).toHaveLength(5));
    expect(screen.getByText("THIRD")).toBeInTheDocument();
  });

  it("shows a field sent holding nothing as left empty, never as a value", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    await waitFor(() => expect(screen.getByText("left empty")).toBeInTheDocument());
    expect(screen.queryByText("null")).not.toBeInTheDocument();
  });

  it("says nothing was recorded rather than inventing a cell", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    await waitFor(() => expect(screen.getByText("not recorded")).toBeInTheDocument());
  });

  it("says which doing proved a field could be left out", async () => {
    const optional = {
      ...version,
      parameters: [{ ...parameter, optional: true, absent_as: "null" }],
    };
    renderWithQuery(<SkillDoings skillId="skl-1" version={optional as never} />);

    await waitFor(() => expect(screen.getByText("optional")).toBeInTheDocument());
    expect(screen.getByText(/left out, some doing sent/)).toBeInTheDocument();
  });

  it("shows only the fields the doings disagree on", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    await waitFor(() => expect(screen.getByText("$work_area")).toBeInTheDocument());
    // `facility` is "SG" in all four — the row is what the skill fixes, not
    // what it asks for, and it is hidden until asked for.
    expect(screen.queryByText("$facility")).not.toBeInTheDocument();
    expect(screen.getByText(/1 field is the same in every doing and hidden/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /show 1 that agrees/i }));
    await waitFor(() => expect(screen.getByText("$facility")).toBeInTheDocument());
  });

  it("counts a field one doing left empty as differing, not as agreeing", async () => {
    // Every doing that answers sent the same value except rec-3, which sent it
    // holding nothing. That is the whole evidence for an optional field, and
    // folding it in with the others would hide the row a reviewer came for.
    const sameButOne = [
      doing("rec-1", { work_area: "SG" }, true),
      doing("rec-2", { work_area: "SG" }, true),
      doing("rec-3", { work_area: null }),
    ];
    vi.spyOn(skills, "getDoings").mockResolvedValue(sameButOne as never);
    renderWithQuery(
      <SkillDoings skillId="skl-1" version={{ ...version, parameters: [parameter] } as never} />,
    );

    await waitFor(() => expect(screen.getByText("left empty")).toBeInTheDocument());
    expect(screen.getByText("$work_area")).toBeInTheDocument();
    expect(screen.queryByText(/the same in every doing and hidden/i)).not.toBeInTheDocument();
  });

  it("says the evidence could not be read rather than disappearing", async () => {
    // A section that vanishes on a failed request reads as "this version has
    // no demonstrations", which is a different and much worse claim.
    vi.spyOn(skills, "getDoings").mockRejectedValue(new Error("404 not found"));
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    await waitFor(() => expect(screen.getByText(/could not be read/i)).toBeInTheDocument());
  });

  it("says so when every demonstration has aged out", async () => {
    vi.spyOn(skills, "getDoings").mockResolvedValue([] as never);
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    await waitFor(() => expect(screen.getByText(/aged out of retention/i)).toBeInTheDocument());
  });

  it("marks the column holding the doings that were actually diffed", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    // Both diffed doings share one shape, so one column carries the mark.
    await waitFor(() => expect(screen.getAllByText("diffed")).toHaveLength(1));
  });

  it("names the individual doings behind a shared column", async () => {
    renderWithQuery(<SkillDoings skillId="skl-1" version={version as never} />);

    await waitFor(() => expect(screen.getByText("2 doings")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /which ones/i }));

    await waitFor(() => expect(screen.getAllByText(/4 steps/).length).toBeGreaterThan(1));
  });
});
