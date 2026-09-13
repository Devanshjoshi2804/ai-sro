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
import * as workflowApi from "@/features/workflow/api";

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
  it("says the schedule could not be read rather than that nothing is scheduled", async () => {
    // The two are not the same claim, and the second one is the sort a person
    // acts on: they would go and create a trigger that already exists.
    vi.spyOn(triggerApi, "listTriggers").mockRejectedValue(new Error("503 service unavailable"));
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);

    show();

    expect(await screen.findByText(/could not be read/i)).toBeInTheDocument();
    expect(screen.queryByText(/nothing runs on a clock yet/i)).not.toBeInTheDocument();
  });

  it("says what it is still waiting for rather than only greying the button", async () => {
    // A disabled control that does not name what it wants is a control people
    // work around, and this one starts a warehouse write on a schedule.
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      { id: "skl-1", name: "Adjust an LPN" },
    ] as never);

    show();
    await screen.findByRole("option", { name: "Adjust an LPN" });

    expect(screen.getByRole("button", { name: "Schedule it" })).toBeDisabled();
    expect(screen.getByText(/still needed: something to run/i)).toBeInTheDocument();

    await userEvent.setup().selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");
    expect(screen.queryByText(/still needed/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Schedule it" })).toBeEnabled();
  });

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
    await user.selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");
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
    await user.selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");
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
    await user.selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");
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
    await user.selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");
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
    await user.selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");
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

describe("a skill that touches two systems", () => {
  it("cannot be put on a clock with nowhere to run", async () => {
    // The server holds one system's credentials at most, so this schedule would
    // be refused at every fire. A trigger that never runs is worse than one
    // that was never made.
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      {
        id: "skl-1",
        name: "Close waves, then record the receipt",
        systems: ["blue_yonder", "sap"],
      },
    ] as never);

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Close waves, then record the receipt" });
    await user.selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");

    expect(screen.getByRole("option", { name: "on the server, as calls" })).toBeDisabled();
    expect(screen.getByText(/signed in to both/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Schedule it" })).toBeDisabled();
  });

  it("replays its calls out of that browser rather than driving the screen", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([
      {
        id: "skl-1",
        name: "Close waves, then record the receipt",
        systems: ["blue_yonder", "sap"],
      },
    ] as never);
    const created = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Close waves, then record the receipt" });
    await user.selectOptions(screen.getByLabelText("What runs"), "skill:skl-1");
    await user.selectOptions(screen.getByLabelText("Where it runs"), "dev-1");
    await user.click(screen.getByRole("button", { name: "Schedule it" }));

    await waitFor(() => expect(created).toHaveBeenCalled());
    // Naming a browser usually means "drive the interface". Here it means the
    // opposite: the steps are calls, and the browser is there for the session
    // each system's own tab holds.
    expect(created.mock.calls[0][0]).toMatchObject({ device_id: "dev-1", medium: "network" });
  });
});

describe("a mined job on a clock", () => {
  /**
   * Until a trigger could name one, nothing but a person accepting an offer in
   * the panel could ever start a job. What these check is that the two things
   * a job cannot do without — a browser, and a name behind it — are refused on
   * the page rather than after the press.
   */
  const JOB = {
    id: "wfl_1",
    title: "Create a work area",
    narrative: "the operator created a work area",
    systems: ["blue_yonder"],
    pass_id: "pass-1",
    parameters: [{ name: "clientCode" }],
    unproven: [],
    steps: [],
    runs: { total: 0, held: 0, earned: false },
  } as unknown as workflowApi.WorkflowModel;

  it("offers the proven jobs and not the ones an offer would never be made for", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([
      JOB,
      { ...JOB, id: "wfl_2", title: "Half a job", unproven: ["step 1 cites nothing"] },
    ]);

    show();

    expect(await screen.findByRole("option", { name: "Create a work area" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Half a job" })).not.toBeInTheDocument();
  });

  it("will not schedule one without a browser and a name behind it", async () => {
    // A job is a recording of somebody's own window: there is no headless path
    // for one, and driving a real browser through real work needs a name.
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([JOB]);

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Create a work area" });
    await user.selectOptions(screen.getByLabelText("What runs"), "job:wfl_1");

    expect(screen.getByRole("option", { name: "on the server, as calls" })).toBeDisabled();
    expect(screen.getByText(/a browser to run it in, your name behind it/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Schedule it" })).toBeDisabled();
  });

  it("names the job rather than a skill, and runs it in that browser", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([JOB]);
    const created = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Create a work area" });
    await user.selectOptions(screen.getByLabelText("What runs"), "job:wfl_1");
    await user.selectOptions(screen.getByLabelText("Where it runs"), "dev-1");
    await user.click(screen.getByLabelText("I stand behind every run this starts"));
    await user.click(screen.getByRole("button", { name: "Schedule it" }));

    await waitFor(() => expect(created).toHaveBeenCalled());
    // Exactly one of the two, which is the rule `Trigger` keeps.
    expect(created.mock.calls[0][0]).toMatchObject({
      workflow_id: "wfl_1",
      skill_id: null,
      device_id: "dev-1",
      medium: "ui",
      authorized_by: true,
      auto_approve: false,
    });
  });

  it("shows an existing job trigger by its title, not by its id", async () => {
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    vi.spyOn(skillApi, "listSkills").mockResolvedValue([] as never);
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([JOB]);
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([
      aTrigger({ skill_id: null, workflow_id: "wfl_1", device_id: "dev-1", medium: "ui" }),
    ]);

    show();

    // The row, not the option of the same name in the picker below it.
    const row = await screen.findByRole("row", { name: /Create a work area/ });
    expect(row).toBeInTheDocument();
    expect(screen.getByText(/a mined job/)).toBeInTheDocument();
  });
});
