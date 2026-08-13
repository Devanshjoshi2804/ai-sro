import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { SkillDetail } from "@/features/skill/components/skill-detail";
import * as api from "@/features/skill/api";

/**
 * The review screen is where a supervisor decides whether a skill is safe to
 * promote. What it must never do is make an unsafe skill look ready.
 */
const version = {
  version: 1,
  stage: "recorded",
  induced_at: "2026-03-01T09:00:00Z",
  induced_by: "clerk@acme.test",
  recording_ids: ["rec-1", "rec-2"],
  provenance_note: "induced from two silent demonstrations",
  steps: [
    {
      index: 0,
      intent: "Release the wave",
      requires_human: false,
      network_plan: {
        method: "POST",
        url: "https://wms.test/api/waves/${wave_id}/release",
        headers: { Authorization: "<blue_yonder/DC01/authorization>" },
        body: null,
        expected_status: 200,
        replayable: true,
        unreplayable_reason: null,
        required_credentials: ["blue_yonder/DC01/authorization"],
      },
      ui_plan: null,
      assertions: [{ kind: "http_status", expected: "200", pointer: null }],
    },
  ],
  parameters: [
    {
      name: "wave_id",
      kind: "input",
      description: "varies between runs",
      observed_values: ["W-1001", "W-2002"],
      source_step_index: null,
    },
  ],
};

const skill = {
  id: "skl-1",
  name: "Release Wave",
  objective_key: {
    objective_type: "release_wave",
    target_system: "blue_yonder",
    entity_type: "wave",
    facility: "DC01",
    direction: "outbound" as const,
  },
  created_at: "2026-03-01T09:00:00Z",
  latest_version: 1,
  latest_stage: "recorded",
  versions: [version],
};

describe("SkillDetail", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows the evidence a parameter was inferred from", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue(skill as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(await screen.findByText("$wave_id")).toBeInTheDocument();
    // Both observed values, or the reviewer cannot tell why it varies.
    expect(screen.getByText(/W-1001 \/ W-2002/)).toBeInTheDocument();
  });

  it("never shows a credential value, only its vault reference", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue(skill as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);
    await screen.findByText("$wave_id");

    expect(screen.getByText(/blue_yonder\/DC01\/authorization/)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("Bearer");
  });

  it("offers only the next rung of the promotion ladder", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue(skill as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(await screen.findByRole("button", { name: /promote to shadow/i })).toBeEnabled();
    expect(screen.queryByRole("button", { name: /autonomous/i })).not.toBeInTheDocument();
  });

  it("stops offering promotion once the highest permitted stage is reached", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      latest_stage: "shadow",
      versions: [{ ...version, stage: "shadow" }],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    const button = await screen.findByRole("button", { name: /highest permitted stage/i });
    expect(button).toBeDisabled();
  });

  it("promotes the version the reviewer is looking at", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue(skill as never);
    const promote = vi
      .spyOn(api, "promoteSkill")
      .mockResolvedValue({ ...version, stage: "shadow" } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);
    await userEvent.click(await screen.findByRole("button", { name: /promote to shadow/i }));

    await waitFor(() => expect(promote).toHaveBeenCalledWith("skl-1", 1, "shadow"));
  });

  it("warns when a step cannot be replayed", async () => {
    const unreplayable = {
      ...skill,
      versions: [
        {
          ...version,
          steps: [
            {
              ...version.steps[0],
              network_plan: {
                ...version.steps[0].network_plan,
                replayable: false,
                unreplayable_reason: "the request carries a client-minted signature",
              },
            },
          ],
        },
      ],
    };
    vi.spyOn(api, "getSkill").mockResolvedValue(unreplayable as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(await screen.findByText(/client-minted signature/)).toBeInTheDocument();
  });
});
