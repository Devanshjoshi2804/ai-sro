import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { RecordingList } from "@/features/recording/components/recording-list";
import * as recordingApi from "@/features/recording/api";
import * as skillApi from "@/features/skill/api";

/**
 * Pairing is the one place this screen can cause real harm: inducing from the
 * wrong two runs produces a skill that looks reviewed and is wrong.
 */
const base = {
  objective_key: {
    objective_type: "release_wave",
    target_system: "blue_yonder",
    entity_type: "wave",
    facility: "DC01",
    direction: "outbound" as const,
  },
  demonstrator: "clerk@acme.test",
  started_at: "2026-03-01T09:00:00Z",
  ended_at: "2026-03-01T09:05:00Z",
  frame_count: 3,
  has_narration: false,
};

const rows = [
  { ...base, id: "sealed-a", label: "run 1", status: "sealed" },
  { ...base, id: "sealed-b", label: "run 2", status: "sealed" },
  { ...base, id: "capturing", label: "in progress", status: "capturing" },
  {
    ...base,
    id: "other-objective",
    label: "counting",
    status: "sealed",
    objective_key: { ...base.objective_key, objective_type: "count_cycle" },
  },
];

const checkbox = (id: string) => screen.getByLabelText(`Select recording ${id}`);

describe("RecordingList", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(recordingApi, "listRecordings").mockResolvedValue(rows as never);
  });

  it("refuses to pair a recording that is still capturing", async () => {
    renderWithQuery(<RecordingList />);
    await screen.findByText("run 1");

    expect(checkbox("capturing")).toBeDisabled();
  });

  it("refuses to pair runs of different objectives", async () => {
    renderWithQuery(<RecordingList />);
    await screen.findByText("run 1");

    await userEvent.click(checkbox("sealed-a"));

    // A different objective would align unrelated steps against each other.
    expect(checkbox("other-objective")).toBeDisabled();
    expect(checkbox("sealed-b")).toBeEnabled();
  });

  it("induces from exactly the two runs that were selected", async () => {
    const induce = vi.spyOn(skillApi, "induceSkill").mockResolvedValue({
      skill_id: "skl-1",
      version: 1,
      step_count: 2,
      input_parameter_count: 1,
      derived_parameter_count: 0,
    } as never);

    renderWithQuery(<RecordingList />);
    await screen.findByText("run 1");

    const button = screen.getByRole("button", { name: /induce skill/i });
    expect(button).toBeDisabled();

    await userEvent.click(checkbox("sealed-a"));
    expect(button).toBeDisabled();

    await userEvent.click(checkbox("sealed-b"));
    expect(button).toBeEnabled();

    await userEvent.click(button);
    expect(induce).toHaveBeenCalledWith("sealed-a", "sealed-b");
  });

  it("stops at two selections", async () => {
    renderWithQuery(<RecordingList />);
    await screen.findByText("run 1");

    await userEvent.click(checkbox("sealed-a"));
    await userEvent.click(checkbox("sealed-b"));

    expect(checkbox("other-objective")).toBeDisabled();
  });
});
