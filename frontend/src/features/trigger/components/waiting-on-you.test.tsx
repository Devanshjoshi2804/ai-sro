import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { WaitingOnYou } from "@/features/trigger/components/waiting-on-you";
import * as triggers from "@/features/trigger/api";
import { toast } from "sonner";
import { ApiError } from "@/lib/api/client";

/**
 * A card here is a warehouse write that has not happened yet, and pressing the
 * button is what makes it happen — now, and under the name of whoever pressed.
 * So what this screen must never do is understate that, or show values other
 * than the ones the run will actually go with.
 */
const waiting = {
  id: "cnf-1",
  trigger_id: "trg-1",
  skill_id: "skl-1",
  skill_name: "Resolve a short ship",
  asked_at: "2026-08-31T09:00:00Z",
  expires_at: "2026-09-01T09:00:00Z",
  values: { shipment_id: "SH-4471", facility: "BLR1" },
  because: "Short ship on PO 88213",
  answer: "waiting",
};

vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(triggers, "listConfirmations").mockResolvedValue([waiting] as never);
  vi.spyOn(triggers, "approveConfirmation").mockResolvedValue({} as never);
  vi.spyOn(triggers, "declineConfirmation").mockResolvedValue({} as never);
});

describe("fires waiting for somebody to say yes", () => {
  it("shows what the run would go with, not just that something fired", async () => {
    renderWithQuery(<WaitingOnYou />);

    await waitFor(() => expect(screen.getByText("SH-4471")).toBeInTheDocument());
    expect(screen.getByText("BLR1")).toBeInTheDocument();
    expect(screen.getByText(/Short ship on PO 88213/)).toBeInTheDocument();
  });

  it("says the press writes and carries the presser's name", async () => {
    // Understating this is how a governance gate becomes a button people press
    // without reading. The run does not carry the trigger author's name.
    renderWithQuery(<WaitingOnYou />);

    await waitFor(() =>
      expect(screen.getByText(/writes to the warehouse, and the run will carry your name/i)).toBeInTheDocument(),
    );
  });

  it("starts nothing until somebody presses", async () => {
    renderWithQuery(<WaitingOnYou />);
    await waitFor(() => expect(screen.getByText("SH-4471")).toBeInTheDocument());

    expect(triggers.approveConfirmation).not.toHaveBeenCalled();
  });

  it("runs it on the press", async () => {
    renderWithQuery(<WaitingOnYou />);
    await waitFor(() => expect(screen.getByText("SH-4471")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /run it now/i }));

    await waitFor(() => expect(triggers.approveConfirmation).toHaveBeenCalledWith("cnf-1"));
  });

  it("asks why before declining, and sends what was written", async () => {
    renderWithQuery(<WaitingOnYou />);
    await waitFor(() => expect(screen.getByText("SH-4471")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /^decline$/i }));
    await userEvent.type(screen.getByPlaceholderText(/why not/i), "wrong dock");
    await userEvent.click(screen.getByRole("button", { name: /^decline$/i }));

    await waitFor(() =>
      expect(triggers.declineConfirmation).toHaveBeenCalledWith("cnf-1", "wrong dock"),
    );
  });

  it("says what the backend refused rather than a generic failure", async () => {
    // The refusals name the thing: it expired, it was already answered, the
    // trigger was switched off since. All of those tell somebody what to do.
    vi.spyOn(triggers, "approveConfirmation").mockRejectedValue(
      new ApiError({ detail: "this expired without an answer" } as never),
    );
    renderWithQuery(<WaitingOnYou />);
    await waitFor(() => expect(screen.getByText("SH-4471")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /run it now/i }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "Not answered",
        expect.objectContaining({ description: "this expired without an answer" }),
      ),
    );
  });

  it("says nothing is waiting rather than showing an empty page", async () => {
    vi.spyOn(triggers, "listConfirmations").mockResolvedValue([] as never);
    renderWithQuery(<WaitingOnYou />);

    await waitFor(() => expect(screen.getByText(/Nothing is waiting/i)).toBeInTheDocument());
  });
});
