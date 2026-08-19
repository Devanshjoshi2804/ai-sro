import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SkillCard } from "@/features/console/skill-card";
import * as skillApi from "@/features/skill/api";
import * as runApi from "@/features/run/api";
import * as chatApi from "@/features/console/chat-api";

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
