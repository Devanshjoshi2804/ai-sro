/**
 * The screen where somebody decides what runs while nobody is watching.
 *
 * What these check is not that the form renders. It is that the three
 * permissions stay three separate decisions with none of them on by default,
 * that nothing is scheduled without a job, a browser and a name behind it, and
 * that the list says in words what fires each trigger and whether it will --
 * the board this replaced printed `arrival` and a cron expression, and showed
 * whether a trigger was on only by which button it offered.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TriggerBoard } from "@/features/trigger/components/trigger-board";
import * as triggerApi from "@/features/trigger/api";
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

const JOB = {
  id: "wfl-1",
  title: "Create a work area",
  narrative: "",
  systems: ["https://wms.example"],
  pass_id: "pas-1",
  parameters: [],
  steps: [],
  runs: { total: 0, held: 0, stale: 0, earned: false },
} as unknown as workflowApi.WorkflowModel;

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
    skill_id: null,
    workflow_id: JOB.id,
    kind: "schedule",
    cron: "0 7 * * 1-5",
    timezone: "Asia/Kolkata",
    parameters: {},
    device_id: DEVICE.id,
    medium: "ui",
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

function given(triggers: triggerApi.TriggerModel[] = []) {
  vi.spyOn(triggerApi, "listTriggers").mockResolvedValue(triggers);
  vi.spyOn(triggerApi, "listDevices").mockResolvedValue([DEVICE]);
  vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([JOB]);
}

afterEach(() => vi.restoreAllMocks());

describe("the list", () => {
  it("says the triggers could not be read rather than that nothing is scheduled", async () => {
    // Not the same claim, and the second is the sort a person acts on: they
    // would go and create a trigger that already exists.
    vi.spyOn(triggerApi, "listTriggers").mockRejectedValue(new Error("503 service unavailable"));
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([]);

    show();

    expect(await screen.findByText(/could not be read/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /put a job on a schedule/i })).toBeNull();
  });

  it("names a job by its title and links to it, not by its id", async () => {
    given([aTrigger()]);

    show();

    const link = await screen.findByRole("link", { name: JOB.title });
    expect(link).toHaveAttribute("href", `/jobs/${JOB.id}`);
    expect(screen.queryByText(JOB.id)).toBeNull();
  });

  it("says in words what fires it, not the expression", async () => {
    given([aTrigger()]);

    show();

    expect(await screen.findByText(/every weekday at 07:00/i)).toBeInTheDocument();
  });

  it("says an arrival is a page somebody opens, not the word arrival", async () => {
    given([
      aTrigger({
        kind: "arrival",
        cron: null,
        arrival: { page: "https://portal.example/inventory" },
      } as Partial<triggerApi.TriggerModel>),
    ]);

    show();

    expect(await screen.findByText(/when an operator opens portal\.example/i)).toBeInTheDocument();
    expect(screen.queryByText(/^arrival$/)).toBeNull();
  });

  it("names only the host when the page was stored without a scheme", async () => {
    // How the real store holds an arrival: no scheme, a whole Keycloak realm
    // path after the host. Parsed as a URL it fails, and the first version
    // printed all hundred characters of it into the sentence.
    given([
      aTrigger({
        kind: "arrival",
        cron: null,
        arrival: { page: "keycloak.example/auth/realms/bf56/protocol/openid-connect/auth" },
      } as Partial<triggerApi.TriggerModel>),
    ]);

    show();

    expect(await screen.findByText("When an operator opens keycloak.example")).toBeInTheDocument();
    expect(screen.queryByText(/realms/)).toBeNull();
  });

  it("says whether each trigger will fire, and why a paused one is paused", async () => {
    given([
      aTrigger(),
      aTrigger({
        id: "trg-2",
        enabled: false,
        disabled_reason: "the operator wants to be asked first",
      }),
    ]);

    show();

    expect(await screen.findByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Paused")).toBeInTheDocument();
    expect(screen.getByText(/the operator wants to be asked first/)).toBeInTheDocument();
    expect(screen.getByText(/1 active · 1 paused/)).toBeInTheDocument();
  });

  it("says when a trigger may bring its tab to the front", async () => {
    given([aTrigger({ may_take_focus: true })]);

    show();

    expect(await screen.findByText(/may bring its tab to the front/i)).toBeInTheDocument();
  });

  it("keeps the form closed until somebody asks for it, once something is scheduled", async () => {
    // The old board was a table above a form three paragraphs of permissions
    // long, so what was actually scheduled was the smaller half of its page.
    given([aTrigger()]);

    show();

    await screen.findByRole("link", { name: JOB.title });
    expect(screen.queryByRole("heading", { name: /put a job on a schedule/i })).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: /new trigger/i }));
    expect(screen.getByRole("heading", { name: /put a job on a schedule/i })).toBeInTheDocument();
  });
});

describe("putting a job on a schedule", () => {
  it("opens straight to the form when nothing is scheduled yet", async () => {
    given([]);

    show();

    expect(
      await screen.findByRole("heading", { name: /put a job on a schedule/i }),
    ).toBeInTheDocument();
  });

  it("says what it is still waiting for rather than only greying the button", async () => {
    // A disabled control that does not name what it wants is a control people
    // work around, and this one starts a warehouse write on a schedule.
    given([]);

    show();

    const button = await screen.findByRole("button", { name: /schedule it/i });
    expect(button).toBeDisabled();
    expect(screen.getByText(/still needs a job, your name behind it/i)).toBeInTheDocument();
  });

  it("asks for the three permissions separately, and none is on to begin with", async () => {
    given([]);

    show();

    for (const name of [
      /i stand behind every run/i,
      /send writes without asking/i,
      /bring its tab to the front/i,
    ]) {
      expect(await screen.findByRole("checkbox", { name })).not.toBeChecked();
    }
  });

  it("will not let a tab be brought to the front with no browser to bring it in", async () => {
    vi.spyOn(triggerApi, "listTriggers").mockResolvedValue([]);
    // Two browsers, so none is chosen for the person.
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([
      DEVICE,
      { ...DEVICE, id: "dev-2", label: "priya" },
    ]);
    vi.spyOn(workflowApi, "listWorkflows").mockResolvedValue([JOB]);

    show();

    expect(await screen.findByRole("checkbox", { name: /bring its tab/i })).toBeDisabled();
    expect(
      screen.getByText(/still needs a job, a browser, your name behind it/i),
    ).toBeInTheDocument();
  });

  it("builds the schedule from what was chosen, and shows it in words", async () => {
    given([]);

    show();

    await userEvent.selectOptions(await screen.findByLabelText("When"), "daily");
    const time = screen.getByLabelText("Time");
    await userEvent.clear(time);
    await userEvent.type(time, "18:30");

    expect(screen.getByText("30 18 * * *")).toBeInTheDocument();
    expect(screen.getByText(/every day at 18:30/i)).toBeInTheDocument();
  });

  it("still takes an expression somebody wrote, and says so when it cannot read it", async () => {
    given([]);

    show();

    await userEvent.selectOptions(await screen.findByLabelText("When"), "custom");
    const expression = screen.getByLabelText("Cron expression");
    await userEvent.clear(expression);
    await userEvent.type(expression, "*/5 9-17 1 * *");

    expect(screen.getByText(/cannot be put in words/i)).toBeInTheDocument();
  });

  it("names the job, runs it in the chosen browser, and sends only what was asked", async () => {
    given([]);
    const create = vi.spyOn(triggerApi, "createTrigger").mockResolvedValue(aTrigger());

    show();

    await userEvent.selectOptions(await screen.findByLabelText("Job"), JOB.id);
    // One browser connected, so it is already chosen.
    expect(screen.getByLabelText("Browser")).toHaveValue(DEVICE.id);
    await userEvent.click(screen.getByRole("checkbox", { name: /i stand behind every run/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /bring its tab/i }));
    await userEvent.click(screen.getByRole("button", { name: /schedule it/i }));

    await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
    expect(create.mock.calls[0][0]).toMatchObject({
      workflow_id: JOB.id,
      skill_id: null,
      kind: "schedule",
      medium: "ui",
      device_id: DEVICE.id,
      authorized_by: true,
      auto_approve: false,
      may_take_focus: true,
    });
  });

  it("offers only jobs to schedule, never a skill from the old path", async () => {
    given([]);

    show();

    const picker = await screen.findByLabelText("Job");
    const labels = within(picker)
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(labels).toEqual(["Choose a job", JOB.title]);
  });
});
