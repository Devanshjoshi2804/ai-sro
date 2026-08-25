/**
 * The screen where somebody decides what runs while nobody is watching.
 *
 * Written because the endpoints existed for weeks with no screen at all, so a
 * trigger could only be created with curl — and `may_take_focus`, which is
 * plumbed from the trigger through the run to the browser, had no way to be
 * turned on by a person at all.
 *
 * What these check is not that the form renders. It is that the three
 * permissions stay three separate decisions, and that none of them is on by
 * default: each is a different thing to regret at three in the morning, and a
 * single "enable automation" switch would grant all of them at once.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TriggerBoard } from "@/features/trigger/components/trigger-board";
import * as triggerApi from "@/features/trigger/api";
import * as skillApi from "@/features/skill/api";

const DEVICE = {
  id: "dev-1",
  principal_id: "devansh",
  label: "devansh",
  extension_version: "0.1.0",
  registered_at: "2026-08-25T08:00:00Z",
  last_seen_at: "2026-08-25T09:00:00Z",
  paused: false,
  queued_events: 0,
  queued_bytes: 0,
  uploads: 3,
} as triggerApi.DeviceModel;

function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <TriggerBoard />
    </QueryClientProvider>,
  );
}

function aTrigger(over: Partial<triggerApi.TriggerModel> = {}): triggerApi.TriggerModel {
  return {
    id: "trg-1",
    skill_id: "skl-1",
    kind: "schedule",
    cron: "0 7 * * 1-5",
    timezone: "Asia/Kolkata",
    parameters: {},
    device_id: null,
    medium: "network",
    enabled: true,
    writes: true,
    authorized_by: "devansh",
    requires_confirmation: true,
    may_take_focus: false,
    created_by: "devansh",
    created_at: "2026-08-25T09:00:00Z",
    last_fired_at: null,
    last_run_id: null,
    disabled_reason: null,
    inbound_token: null,
    ...over,
  } as triggerApi.TriggerModel;
}

afterEach(() => vi.restoreAllMocks());

describe("putting a skill on a clock", () => {
  it("asks for the three permissions separately, and none is on to begin with", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      { id: "skl-1", name: "Adjust an LPN" },
    ] as never);
    const created = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();
    const user = userEvent.setup();
    // Waits for the skill list to arrive: a select with no options yet is a
    // select nobody can choose from, which is also true of the real screen.
    await screen.findByRole("option", { name: "Adjust an LPN" });
    await user.selectOptions(screen.getByLabelText("Skill"), "skl-1");
    await user.click(screen.getByRole("button", { name: "Schedule it" }));

    await waitFor(() => expect(created).toHaveBeenCalled());
    // Off unless somebody said so, every one of them.
    expect(created.mock.calls[0][0]).toMatchObject({
      authorized_by: false,
      auto_approve: false,
      may_take_focus: false,
    });
  });

  it("sends may_take_focus only when it was asked for, and nothing else with it", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      { id: "skl-1", name: "Adjust an LPN" },
    ] as never);
    const created = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Adjust an LPN" });
    await user.selectOptions(screen.getByLabelText("Skill"), "skl-1");
    // A browser first. A schedule that runs on the server has no screen to
    // take, so the permission is not offered until one is named.
    await user.selectOptions(screen.getByLabelText("Where it runs"), "dev-1");
    await user.click(screen.getByLabelText("May bring a tab to the front"));
    await user.click(screen.getByRole("button", { name: "Schedule it" }));

    await waitFor(() => expect(created).toHaveBeenCalled());
    // The whole point of three checkboxes: taking somebody's screen is not the
    // same permission as writing to their warehouse unattended.
    expect(created.mock.calls[0][0]).toMatchObject({
      may_take_focus: true,
      device_id: "dev-1",
      medium: "ui",
      authorized_by: false,
      auto_approve: false,
    });
  });
});

describe("choosing when it runs", () => {
  it("builds the schedule from what was chosen, and shows it in words", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      { id: "skl-1", name: "Adjust an LPN" },
    ] as never);
    const created = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Adjust an LPN" });
    await user.selectOptions(screen.getByLabelText("Skill"), "skl-1");
    await user.selectOptions(screen.getByLabelText("When"), "weekly");
    await user.selectOptions(screen.getByLabelText("Day"), "3");

    // Said back in words, because `0 7 * * 3` firing on the wrong day is a typo
    // nobody can see in the expression itself.
    expect(screen.getByText(/every Wednesday at 07:00/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Schedule it" }));
    await waitFor(() => expect(created).toHaveBeenCalled());
    expect(created.mock.calls[0][0]).toMatchObject({ cron: "0 7 * * 3" });
  });

  it("still takes an expression somebody wrote, and says so when it cannot read it", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      { id: "skl-1", name: "Adjust an LPN" },
    ] as never);
    const created = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Adjust an LPN" });
    await user.selectOptions(screen.getByLabelText("Skill"), "skl-1");
    await user.selectOptions(screen.getByLabelText("When"), "custom");
    const written = screen.getByLabelText("Cron expression");
    await user.clear(written);
    await user.type(written, "0 7 1 * *");

    // The scheduler understands more than this screen does. Saying so beats
    // refusing an expression the backend would have accepted.
    expect(screen.getByText(/cannot put it in words/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Schedule it" }));
    await waitFor(() => expect(created).toHaveBeenCalled());
    expect(created.mock.calls[0][0]).toMatchObject({ cron: "0 7 1 * *" });
  });
});

describe("what is already on a clock", () => {
  it("says who stands behind a write and whether it asks first", async () => {
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([
      aTrigger({ requires_confirmation: false, authorized_by: "devansh" }),
    ]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);

    show();

    // A write that goes out unattended must never be a row that looks like
    // every other row.
    expect(await screen.findByText("sends without asking")).toBeInTheDocument();
    expect(screen.getByText(/devansh stands behind it/)).toBeInTheDocument();
  });

  it("says when a trigger may take the operator's screen", async () => {
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([aTrigger({ may_take_focus: true })]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);

    show();

    expect(await screen.findByText("may take the screen")).toBeInTheDocument();
  });

  it("pauses by removing the schedule rather than by letting it fire into a check", async () => {
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([aTrigger()]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);
    const paused = vi
      .spyOn(triggerApi, "setTriggerEnabled")
      .mockResolvedValue(aTrigger({ enabled: false }));

    show();
    await userEvent.setup().click(await screen.findByRole("button", { name: "Pause" }));

    await waitFor(() => expect(paused).toHaveBeenCalledWith("trg-1", false, expect.any(String)));
  });
});


describe("a permission that could not reach anything", () => {
  it("cannot be given to a schedule that runs on the server", async () => {
    // It was ticked, stored and displayed, and never reached a run: a trigger
    // with no device takes the durable path, which has no browser and passes no
    // focus decision. A checkbox that lies is worse than one that is missing.
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      { id: "skl-1", name: "Adjust an LPN" },
    ] as never);

    show();
    await screen.findByRole("option", { name: "Adjust an LPN" });

    expect(screen.getByLabelText("May bring a tab to the front")).toBeDisabled();
    expect(screen.getByText(/choose one above/)).toBeInTheDocument();
  });

  it("is dropped again if the browser is taken away after ticking it", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      { id: "skl-1", name: "Adjust an LPN" },
    ] as never);
    const created = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Adjust an LPN" });
    await user.selectOptions(screen.getByLabelText("Skill"), "skl-1");
    await user.selectOptions(screen.getByLabelText("Where it runs"), "dev-1");
    await user.click(screen.getByLabelText("May bring a tab to the front"));
    await user.selectOptions(screen.getByLabelText("Where it runs"), "");
    await user.click(screen.getByRole("button", { name: "Schedule it" }));

    await waitFor(() => expect(created).toHaveBeenCalled());
    expect(created.mock.calls[0][0]).toMatchObject({
      device_id: null,
      may_take_focus: false,
    });
  });
});
