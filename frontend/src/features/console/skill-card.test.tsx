import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SkillCard } from "@/features/console/skill-card";
import * as skillApi from "@/features/skill/api";
import * as runApi from "@/features/run/api";
import * as chatApi from "@/features/console/chat-api";
import * as triggerApi from "@/features/trigger/api";

/**
 * The card that holds the button that writes to a warehouse. It had no tests
 * at all, and one of the things it does is decide whether that button can be
 * pressed twice.
 */
function aSkill(overrides: Record<string, unknown> = {}) {
  return {
    id: "skl-1",
    name: "Create a client",
    objective_key: { target_system: "blue_yonder", entity_type: "client", facility: "DC01" },
    versions: [
      {
        version: 1,
        stage: "assisted",
        summary: "Creates a client.",
        parameters: [],
        assertions: [],
        recording_ids: ["rec-1", "rec-2"],
        changes_the_system: true,
        steps: [
          {
            index: 0,
            intent: "post the client",
            assertions: [],
            network_plan: { method: "POST", url: "https://wms.test/clients", headers: {} },
          },
        ],
        ...overrides,
      },
    ],
  } as unknown as Awaited<ReturnType<typeof skillApi.getSkill>>;
}

function renderCard(props: Partial<Parameters<typeof SkillCard>[0]> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SkillCard skillId="skl-1" threadId="thr-1" parameters={{}} {...props} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("the button that writes", () => {
  it("sends the run once, however many times it is pressed", async () => {
    vi.spyOn(skillApi, "getSkill").mockResolvedValue(aSkill());
    const asked = vi
      .spyOn(chatApi, "runInThread")
      // A reply with no run id in it -- a real shape: the backend answers a
      // question rather than starting a run. The button stayed live for it.
      .mockResolvedValue({ messages: [{ decision: {} }] } as never);

    renderCard();
    const button = await screen.findByRole("button", { name: /run it/i });
    await userEvent.click(button);
    await waitFor(() => expect(asked).toHaveBeenCalledTimes(1));
    await userEvent.click(button);

    expect(asked).toHaveBeenCalledTimes(1);
  });

  it("comes back when nothing was started, so a refusal does not strand anybody", async () => {
    vi.spyOn(skillApi, "getSkill").mockResolvedValue(aSkill());
    vi.spyOn(chatApi, "runInThread").mockRejectedValue(new Error("refused"));

    renderCard();
    const button = await screen.findByRole("button", { name: /run it/i });
    await userEvent.click(button);

    await waitFor(() => expect(button).not.toBeDisabled());
  });

  it("cannot be pressed for a version nobody has reviewed", async () => {
    vi.spyOn(skillApi, "getSkill").mockResolvedValue(aSkill({ stage: "recorded" }));
    const started = vi.spyOn(runApi, "startRun");

    renderCard({ threadId: undefined });

    expect(await screen.findByRole("button", { name: /run it/i })).toBeDisabled();
    expect(started).not.toHaveBeenCalled();
  });
});

describe("a skill that touches two systems", () => {
  const BROWSER = {
    id: "dev-1",
    principal_id: "devansh",
    label: "devansh's Chrome",
    extension_version: "0.1.0",
    registered_at: "2026-08-25T08:00:00Z",
    last_seen_at: "2026-08-25T09:00:00Z",
    paused: false,
    queued_events: 0,
    queued_bytes: 0,
    uploads: 3,
  } as triggerApi.DeviceModel;

  it("runs in a browser signed in to both, and says which", async () => {
    vi.spyOn(skillApi, "getSkill").mockResolvedValue(aSkill({ systems: ["blue_yonder", "sap"] }));
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([BROWSER]);
    const started = vi.spyOn(runApi, "startRun").mockResolvedValue({
      id: "run-1",
      status: "succeeded",
      steps: [],
      medium: "network",
    } as never);

    renderCard({ threadId: undefined });
    await userEvent.click(await screen.findByRole("button", { name: /run it/i }));

    // The whole reason a workflow is device-bound: this deployment holds one
    // system's credentials at most, and that browser is signed in to both.
    await waitFor(() =>
      expect(started).toHaveBeenCalledWith(
        "skl-1",
        {},
        expect.objectContaining({ deviceId: "dev-1" }),
      ),
    );
  });

  it("asks first when no browser is connected, rather than being refused", async () => {
    vi.spyOn(skillApi, "getSkill").mockResolvedValue(aSkill({ systems: ["blue_yonder", "sap"] }));
    vi.spyOn(triggerApi, "listDevices").mockResolvedValue([]);
    const started = vi.spyOn(runApi, "startRun");

    renderCard({ threadId: undefined });

    expect(await screen.findByText(/needs a browser signed in to both/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run it/i })).toBeDisabled();
    expect(started).not.toHaveBeenCalled();
  });

  it("leaves an ordinary skill alone: no browser to choose, and none sent", async () => {
    vi.spyOn(skillApi, "getSkill").mockResolvedValue(aSkill({ systems: ["blue_yonder"] }));
    const devices = vi.spyOn(triggerApi, "listDevices").mockResolvedValue([BROWSER]);
    const started = vi.spyOn(runApi, "startRun").mockResolvedValue({
      id: "run-1",
      status: "succeeded",
      steps: [],
      medium: "network",
    } as never);

    renderCard({ threadId: undefined });
    await userEvent.click(await screen.findByRole("button", { name: /run it/i }));

    await waitFor(() => expect(started).toHaveBeenCalled());
    expect(started.mock.calls[0][2]).toMatchObject({ deviceId: null });
    expect(screen.queryByLabelText("Where it runs")).not.toBeInTheDocument();
    // Not even asked for: a run in this deployment's own browser has no device.
    expect(devices).not.toHaveBeenCalled();
  });
});
