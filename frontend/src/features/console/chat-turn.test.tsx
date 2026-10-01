import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { renderWithQuery } from "@/test/render";
import { ChatTurn } from "@/features/console/console";
import * as workflowApi from "@/features/workflow/api";

describe("a job a yes started", () => {
  it("links the run the backend named", () => {
    // S2 review M2: the console drew "Running X now." as text, with no way to
    // reach the run it named.
    render(
      <ChatTurn
        message={{
          id: "m2",
          speaker: "assistant",
          text: "Running Compose and Send Email now.",
          said_at: "2026-09-28T10:20:02Z",
          decision: { kind: "job", workflow_id: "wfl_mail", run_id: "run_7", resume: true },
        }}
      />,
    );

    expect(screen.getByRole("link", { name: "Watch the run" })).toHaveAttribute(
      "href",
      "/jobs/runs/run_7",
    );
  });

  it("links nothing when nothing was started", () => {
    render(
      <ChatTurn
        message={{
          id: "m3",
          speaker: "assistant",
          text: "Nothing was started: none of your browsers is connected.",
          said_at: "2026-09-28T10:20:02Z",
          decision: { kind: "job", workflow_id: "wfl_mail" },
        }}
      />,
    );

    expect(screen.queryByRole("link")).toBeNull();
  });
});

describe("a run asking for its password in the thread", () => {
  beforeEach(() => vi.restoreAllMocks());

  const asked = {
    id: "q_1",
    kind: "password",
    text: "clerk at login.idp.example has no usable password. Enter it on the run's card.",
    origin: "login.idp.example",
    username: "clerk",
    field: "password",
  };
  const message = (question_id: string) => ({
    id: "m9",
    speaker: "assistant" as const,
    text: asked.text,
    said_at: "2026-10-01T10:20:02Z",
    decision: { kind: "run_asks", run_id: "run_1", question_id, asks: "password" },
  });
  const seen = (question: unknown, outcome = "running") =>
    vi
      .spyOn(workflowApi, "getWorkflowRun")
      .mockResolvedValue({ id: "run_1", outcome, question } as never);

  it("draws the box under the message, bound to that run", async () => {
    seen(asked);
    renderWithQuery(<ChatTurn message={message("q_1")} />);

    expect(await screen.findByLabelText("Password")).toHaveAttribute("type", "password");
    expect(workflowApi.getWorkflowRun).toHaveBeenCalledWith("run_1");
  });

  it("draws nothing once that question is answered or another stands", async () => {
    seen({ ...asked, id: "q_2" });
    renderWithQuery(<ChatTurn message={message("q_1")} />);

    await vi.waitFor(() => expect(workflowApi.getWorkflowRun).toHaveBeenCalled());
    expect(screen.queryByLabelText("Password")).toBeNull();
  });

  it("asks the backend nothing for a message that is not a password question", () => {
    seen(asked);
    render(
      <ChatTurn
        message={{ ...message("q_1"), decision: { kind: "run_asks", run_id: "run_1", asks: "value" } }}
      />,
    );
    expect(workflowApi.getWorkflowRun).not.toHaveBeenCalled();
  });
});
