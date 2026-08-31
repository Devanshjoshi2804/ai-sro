import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { MapStepToTool } from "@/features/skill/components/map-step-to-tool";
import * as skills from "@/features/skill/api";
import { toast } from "sonner";
import { ApiError } from "@/lib/api/client";

/**
 * Saying that a click is a tool call.
 *
 * The one part of a skill nobody demonstrates, so it is a decision with a name
 * on it — and the two things this screen must not get wrong are the two things
 * the person is actually deciding: which tool, and whether calling it writes.
 */
const step = {
  index: 1,
  intent: "send the reply",
  requires_human: false,
  narration: "",
  branch_hint: null,
  when: null,
  network_plan: null,
  ui_plan: { action: "click", target: "Send", target_path: null, value: null, wait_for: null },
  tool_plan: null,
  assertions: [],
};

const parameter = {
  name: "supplier",
  kind: "input",
  description: "",
  observed_values: [],
  source_step_index: null,
  options: null,
  optional: false,
  absent_as: null,
  evidence: "proven",
};

const OFFERED = [
  { name: "send_message", description: "Send a mail", arguments: ["to", "body"] },
  { name: "list_messages", description: "Read the inbox", arguments: [] },
];

function render(overrides: Record<string, unknown> = {}) {
  return renderWithQuery(
    <MapStepToTool
      skillId="skl-1"
      version={1}
      step={{ ...step, ...overrides } as never}
      parameters={[parameter] as never}
    />,
  );
}

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(skills, "listOfferedTools").mockResolvedValue(OFFERED as never);
  vi.spyOn(skills, "mapStepToTool").mockResolvedValue({} as never);
});

describe("mapping a click onto a tool", () => {
  it("asks the connector what it offers rather than letting somebody type a name", async () => {
    render();
    await userEvent.click(screen.getByRole("button", { name: /perform this as a call/i }));

    await userEvent.type(screen.getByLabelText("Connector"), "mail");

    await waitFor(() => expect(skills.listOfferedTools).toHaveBeenCalledWith("mail"));
  });

  it("does not ask before a connector has been named", async () => {
    render();
    await userEvent.click(screen.getByRole("button", { name: /perform this as a call/i }));

    expect(skills.listOfferedTools).not.toHaveBeenCalled();
  });

  it("does not claim a call writes unless somebody said so", async () => {
    // Nothing else can tell us: MCP declares no such thing, and a tool named
    // `send_message` is a name rather than a promise. A default of true would
    // withhold every read; a default that guessed from the name would send a
    // mail nobody approved.
    render();
    await userEvent.click(screen.getByRole("button", { name: /perform this as a call/i }));
    await userEvent.type(screen.getByLabelText("Connector"), "mail");
    await waitFor(() => expect(skills.listOfferedTools).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(await screen.findByRole("option", { name: "send_message" }));
    await userEvent.click(screen.getByRole("button", { name: /map this step/i }));

    await waitFor(() =>
      expect(skills.mapStepToTool).toHaveBeenCalledWith(
        "skl-1",
        expect.objectContaining({ tool: "send_message", writes: false, step_index: 1 }),
      ),
    );
  });

  it("says what the backend refused rather than a generic failure", async () => {
    // Every refusal names the thing to fix -- a tool the connector does not
    // offer, a parameter that does not exist, no connector at all -- and a
    // toast saying "something went wrong" throws all of that away.
    vi.spyOn(skills, "mapStepToTool").mockRejectedValue(
      new ApiError({ detail: "mail offers no tool called send_mail" } as never),
    );
    render();
    await userEvent.click(screen.getByRole("button", { name: /perform this as a call/i }));
    await userEvent.type(screen.getByLabelText("Connector"), "mail");
    await waitFor(() => expect(skills.listOfferedTools).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(await screen.findByRole("option", { name: "send_message" }));
    await userEvent.click(screen.getByRole("button", { name: /map this step/i }));

    // Asserted on the call rather than on the rendered toast: the Toaster is
    // mounted by the app shell, not by this component, and a test that needed
    // one would be testing the harness.
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "Not mapped",
        expect.objectContaining({ description: "mail offers no tool called send_mail" }),
      ),
    );
  });

  it("shows what a mapped step calls instead of offering to map it again", async () => {
    render({
      tool_plan: { server: "mail", tool: "send_message", arguments: {}, writes: true },
    });

    expect(screen.getByText(/send_message/)).toBeInTheDocument();
    expect(screen.getByText(/it writes/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /perform this as a call/i }),
    ).not.toBeInTheDocument();
  });
});
