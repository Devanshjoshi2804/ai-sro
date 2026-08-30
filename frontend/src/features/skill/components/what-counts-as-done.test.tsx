import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { WhatCountsAsDone } from "@/features/skill/components/what-counts-as-done";
import * as skills from "@/features/skill/api";
import { toast } from "sonner";
import { ApiError } from "@/lib/api/client";

/**
 * Writing what counts as a step having worked.
 *
 * The thing this screen must not do is offer a question nothing can answer. A
 * tool answers a document — no status code, no screen — so a status check on
 * one would not make the step safer; it would make every run of it fail, which
 * reads exactly like a step that is broken.
 */
const base = {
  index: 1,
  intent: "send the reply",
  requires_human: false,
  narration: "",
  branch_hint: null,
  when: null,
  network_plan: null,
  ui_plan: null,
  tool_plan: { server: "mail", tool: "send_message", arguments: {}, writes: true },
  assertions: [],
};

const network = {
  ...base,
  tool_plan: null,
  network_plan: {
    method: "POST",
    url: "https://wms.test/api/waves",
    headers: {},
    body: null,
    expected_status: 200,
    replayable: true,
    unreplayable_reason: null,
    required_credentials: [],
  },
};

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function render(step: Record<string, unknown> = base) {
  return renderWithQuery(
    <WhatCountsAsDone skillId="skl-1" version={1} step={step as never} />,
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(skills, "addAssertion").mockResolvedValue({} as never);
});

describe("saying what counts as done", () => {
  it("does not offer a tool step a check nothing could ever answer", async () => {
    render();
    await userEvent.click(screen.getByRole("button", { name: /say what counts as done/i }));
    await userEvent.click(screen.getByRole("combobox"));

    expect(await screen.findByRole("option", { name: /a field of the answer is/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /the status is/i })).not.toBeInTheDocument();
  });

  it("offers a status check on a step that is an exchange", async () => {
    render(network);
    await userEvent.click(screen.getByRole("button", { name: /say what counts as done/i }));
    await userEvent.click(screen.getByRole("combobox"));

    expect(await screen.findByRole("option", { name: /the status is/i })).toBeInTheDocument();
  });

  it("sends the field and the value somebody wrote", async () => {
    render();
    await userEvent.click(screen.getByRole("button", { name: /say what counts as done/i }));
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(await screen.findByRole("option", { name: /a field of the answer is/i }));
    await userEvent.type(screen.getByLabelText("Field"), "/status");
    await userEvent.type(screen.getByLabelText("Is"), "sent");
    await userEvent.click(screen.getByRole("button", { name: /add this check/i }));

    await waitFor(() =>
      expect(skills.addAssertion).toHaveBeenCalledWith("skl-1", {
        version: 1,
        step_index: 1,
        kind: "response_field_equals",
        expected: "sent",
        pointer: "/status",
      }),
    );
  });

  it("will not submit a check with nothing to check", async () => {
    render();
    await userEvent.click(screen.getByRole("button", { name: /say what counts as done/i }));

    expect(screen.getByRole("button", { name: /add this check/i })).toBeDisabled();
  });

  it("says what the backend refused rather than a generic failure", async () => {
    vi.spyOn(skills, "addAssertion").mockRejectedValue(
      new ApiError({ detail: "this step already checks that" } as never),
    );
    render();
    await userEvent.click(screen.getByRole("button", { name: /say what counts as done/i }));
    await userEvent.type(screen.getByLabelText("Field"), "/id");
    await userEvent.click(screen.getByRole("button", { name: /add this check/i }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "Not added",
        expect.objectContaining({ description: "this step already checks that" }),
      ),
    );
  });
});
