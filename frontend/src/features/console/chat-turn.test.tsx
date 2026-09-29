import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatTurn } from "@/features/console/console";

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
