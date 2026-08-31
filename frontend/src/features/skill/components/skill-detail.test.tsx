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
  summary: "Release a wave at DC01.",
  when_to_use: "Use to start picking.",
  track_record: {
    clean_streak: 0,
    consecutive_failures: 0,
    clean_runs: 0,
    degraded_runs: 0,
    failed_runs: 0,
    unreachable_runs: 0,
    clean_runs_needed: 10,
    failures_before_demotion: 3,
  },
  ready_for_autonomy: "0 clean runs in a row, 10 needed",
  demotion_reason: null,
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

  it("stops offering promotion at the top of the ladder", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      latest_stage: "autonomous",
      versions: [{ ...version, stage: "autonomous", ready_for_autonomy: null }],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    const button = await screen.findByRole("button", { name: /top of the ladder/i });
    expect(button).toBeDisabled();
  });

  it("says which door a promotion came through, so a reviewer can disagree", async () => {
    // ADR 014 lets an operator promote a version to assisted by reading the
    // panel's own preview and pressing once, and says plainly that the
    // visibility of *which* review happened "is the whole of what this
    // decision buys a reviewer". `promoted_from` was on the wire and rendered
    // nowhere, so that decision bought a reviewer nothing at all.
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      latest_stage: "assisted",
      versions: [{ ...version, stage: "assisted", promoted_from: "preview" }],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(await screen.findByText(/an operator read the steps and the values/i)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("Promoted here");
  });

  it("reads differently for a promotion made in this console", async () => {
    // The other half: naming the panel promotion is only worth anything if a
    // console one is visibly a different thing beside it.
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      latest_stage: "assisted",
      versions: [{ ...version, stage: "assisted", promoted_from: "console" }],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(
      await screen.findByText(/Promoted here, by somebody reading this version's evidence/i),
    ).toBeInTheDocument();
  });

  it("says why a version cannot run unattended yet", async () => {
    // A gate that says no without saying why is a gate people work around.
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      latest_stage: "assisted",
      versions: [{ ...version, stage: "assisted" }],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(await screen.findByText(/0 clean runs in a row, 10 needed/)).toBeInTheDocument();
  });

  it("draws the streak against what it needs, from the backend's own threshold", async () => {
    // A console that hardcoded ten would keep saying ten the day the domain
    // changed its mind, and the bar would disagree with the rule that actually
    // refuses the promotion.
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      versions: [
        {
          ...version,
          track_record: { ...version.track_record, clean_streak: 7, clean_runs_needed: 12 },
        },
      ],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    const meter = await screen.findByRole("meter", { name: /clean runs in a row/i });
    expect(meter).toHaveAttribute("aria-valuenow", "7");
    expect(meter).toHaveAttribute("aria-valuemax", "12");
    expect(screen.getByText(/7 of 12/)).toBeInTheDocument();
  });

  it("says how close a failing version is to being demoted", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      versions: [
        {
          ...version,
          track_record: { ...version.track_record, consecutive_failures: 2 },
        },
      ],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    // A streak only means something beside the thing that would break it.
    expect(await screen.findByText(/2 failures in a row/i)).toBeInTheDocument();
    expect(screen.getByText(/1 more demotes it/i)).toBeInTheDocument();
  });

  it("says nothing about demotion for a version that has never failed", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue(skill as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);
    await screen.findByRole("meter", { name: /clean runs in a row/i });

    expect(screen.queryByText(/in a row\./i)).not.toBeInTheDocument();
    expect(screen.queryByText(/demotes it/i)).not.toBeInTheDocument();
  });

  it("refuses the unattended rung on the page rather than on the click", async () => {
    // The button used to be fully enabled here, with the refusal only in a
    // `title` — invisible on a touchscreen and to a screen reader. Inviting a
    // click the backend will turn down is how a reviewer stops trusting the
    // gate.
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      latest_stage: "assisted",
      versions: [{ ...version, stage: "assisted" }],
    } as never);
    const promote = vi.spyOn(api, "promoteSkill");

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    const button = await screen.findByRole("button", { name: /promote to autonomous/i });
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(promote).not.toHaveBeenCalled();
  });

  it("offers the unattended rung once the record allows it", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      latest_stage: "assisted",
      versions: [{ ...version, stage: "assisted", ready_for_autonomy: null }],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(await screen.findByRole("button", { name: /promote to autonomous/i })).toBeEnabled();
  });

  it("promotes the version the reviewer is looking at", async () => {
    vi.spyOn(api, "getSkill").mockResolvedValue(skill as never);
    const promote = vi
      .spyOn(api, "promoteSkill")
      .mockResolvedValue({ ...version, stage: "shadow" } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);
    await userEvent.click(await screen.findByRole("button", { name: /promote to shadow/i }));

    // The last argument is the acknowledgement a one-demonstration skill needs
    // before it may send fixed values for real. False unless somebody said so.
    await waitFor(() => expect(promote).toHaveBeenCalledWith("skl-1", 1, "shadow", false));
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

describe("a skill that does part of its work once per thing", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("says so above the steps it repeats, and only above the first of them", async () => {
    // A reviewer approving a write has to see that this one is not sent once
    // but once for each line the previous step found. A step list that looks
    // like every other step list hides exactly that.
    vi.spyOn(api, "getSkill").mockResolvedValue({
      ...skill,
      versions: [
        {
          ...version,
          steps: [
            { ...version.steps[0], index: 0, intent: "Open the order" },
            { ...version.steps[0], index: 1, intent: "Adjust the line" },
            { ...version.steps[0], index: 2, intent: "Close the order" },
          ],
          loops: [
            {
              over_step_index: 0,
              over_pointer: "/data/lines",
              first_step: 1,
              last_step: 1,
              binds: { line_id: "/lineId" },
              says: "once for each lines step 0 found",
            },
          ],
        },
      ],
    } as never);

    renderWithQuery(<SkillDetail skillId="skl-1" />);

    expect(await screen.findByText(/once for each lines step 0 found/)).toBeInTheDocument();
    expect(screen.getAllByText(/once for each/)).toHaveLength(1);
  });
});
