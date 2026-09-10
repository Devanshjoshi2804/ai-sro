/**
 * Revoking cuts a browser off mid-shift. The harm this screen can do is fire
 * that on one press, or leave a press armed on a row whose meaning has moved.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithQuery } from "@/test/render";
import { BrowserRoster } from "@/features/workflow/components/browser-roster";
import * as workflowApi from "@/features/workflow/api";

const browser = (over: Partial<workflowApi.DeviceLineModel> = {}) => ({
  device_id: "dev_a",
  principal_id: "devansh",
  label: "Macintosh · Chrome",
  registered_at: "2026-08-26T05:56:55+00:00",
  last_seen_at: "2026-09-10T10:28:28+00:00",
  revoked_at: null,
  online: true,
  ...over,
});

describe("BrowserRoster", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("does not revoke on the first press", async () => {
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([browser()] as never);
    const revoke = vi.spyOn(workflowApi, "revokeBrowser").mockResolvedValue({} as never);
    renderWithQuery(<BrowserRoster />);
    await userEvent.click(await screen.findByRole("button", { name: "revoke" }));
    expect(revoke).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "revoke — sure?" })).toBeInTheDocument();
  });

  it("revokes on the second press", async () => {
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([browser()] as never);
    const revoke = vi.spyOn(workflowApi, "revokeBrowser").mockResolvedValue({} as never);
    renderWithQuery(<BrowserRoster />);
    await userEvent.click(await screen.findByRole("button", { name: "revoke" }));
    await userEvent.click(screen.getByRole("button", { name: "revoke — sure?" }));
    await waitFor(() => expect(revoke).toHaveBeenCalledWith("dev_a"));
  });

  it("disarms a half-pressed revoke when anything in the list changes", async () => {
    const list = vi
      .spyOn(workflowApi, "listBrowsers")
      .mockResolvedValue([browser(), browser({ device_id: "dev_b", online: true })] as never);
    renderWithQuery(<BrowserRoster />);
    const first = await screen.findAllByRole("button", { name: "revoke" });
    await userEvent.click(first[0]);
    expect(screen.getByRole("button", { name: "revoke — sure?" })).toBeInTheDocument();

    // dev_b goes offline. Nothing about dev_a changed, and dev_a disarms anyway.
    list.mockResolvedValue([browser(), browser({ device_id: "dev_b", online: false })] as never);
    await waitFor(
      () => expect(screen.queryByRole("button", { name: "revoke — sure?" })).toBeNull(),
      { timeout: 5000 },
    );
  });

  it("offers restore, and not revoke, on a browser already cut off", async () => {
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([
      browser({ revoked_at: "2026-09-10T14:32:07+00:00" }),
    ] as never);
    renderWithQuery(<BrowserRoster />);
    expect(await screen.findByRole("button", { name: "restore" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "revoke" })).toBeNull();
    expect(screen.getByText(/revoked 2026-09-10 14:32:07/)).toBeInTheDocument();
  });

  it("says why a revoke was refused and does not pretend it worked", async () => {
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([browser()] as never);
    vi.spyOn(workflowApi, "revokeBrowser").mockRejectedValue(new Error("browser is busy"));
    renderWithQuery(<BrowserRoster />);
    await userEvent.click(await screen.findByRole("button", { name: "revoke" }));
    await userEvent.click(screen.getByRole("button", { name: "revoke — sure?" }));
    expect(await screen.findByText(/browser is busy/)).toBeInTheDocument();
  });

  it("tells an operator with no browsers what to do about it", async () => {
    vi.spyOn(workflowApi, "listBrowsers").mockResolvedValue([] as never);
    renderWithQuery(<BrowserRoster />);
    expect(await screen.findByText(/no browser has registered/i)).toBeInTheDocument();
  });
});
