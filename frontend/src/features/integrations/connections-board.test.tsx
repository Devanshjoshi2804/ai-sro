import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConnectionsBoard } from "@/features/integrations/connections-board";
import * as integrationApi from "@/features/integrations/api";
import { ApiError } from "@/lib/api/client";
import { renderWithQuery } from "@/test/render";

vi.mock("@/features/integrations/api", async (importActual) => ({
  ...(await importActual<typeof integrationApi>()),
  listIntegrations: vi.fn(),
  createConnectSession: vi.fn(),
}));

const nango = vi.hoisted(() => ({
  options: [] as unknown[],
  tokens: [] as unknown[],
  close: vi.fn(),
}));
vi.mock("@nangohq/frontend", () => ({
  default: class {
    constructor(config: unknown) {
      nango.tokens.push(config);
    }
    openConnectUI(params: unknown) {
      nango.options.push(params);
      return { close: nango.close };
    }
  },
}));

const list = vi.mocked(integrationApi.listIntegrations);
const session = vi.mocked(integrationApi.createConnectSession);
const SESSION = { token: "tok", connect_url: "http://connect.test", api_url: "http://api.test" };
const OFF = { integration: "microsoft", connected: false, connected_at: null };

type Handler = (event: { type: string }) => void;
const onEvent = () => (nango.options.at(-1) as { onEvent: Handler }).onEvent;

beforeEach(() => {
  vi.resetAllMocks();
  nango.options.length = 0;
  nango.tokens.length = 0;
  nango.close.mockReset();
  session.mockResolvedValue(SESSION);
});

describe("ConnectionsBoard", () => {
  it("lists Outlook as not connected with a Connect button", async () => {
    list.mockResolvedValue([OFF]);
    renderWithQuery(<ConnectionsBoard />);
    expect(await screen.findByText(/Outlook — not connected/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect Outlook" })).toBeEnabled();
  });

  it("opens the Connect UI with the session's own URLs", async () => {
    list.mockResolvedValue([OFF]);
    renderWithQuery(<ConnectionsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Outlook" }));
    await waitFor(() => expect(nango.options).toHaveLength(1));
    expect(session).toHaveBeenCalledWith("microsoft");
    expect(nango.tokens[0]).toEqual({ connectSessionToken: "tok" });
    expect(nango.options[0]).toEqual({
      baseURL: "http://connect.test",
      apiURL: "http://api.test",
      onEvent: expect.any(Function),
    });
    const busy = screen.getByRole("button", { name: "Connecting Outlook…" });
    expect(busy).toBeDisabled();
    expect(busy).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("status")).toHaveTextContent("Connecting Outlook");
  });

  it("disables the other rows' Connect buttons while one is busy", async () => {
    list.mockResolvedValue([OFF, { ...OFF, integration: "google-mail" }]);
    renderWithQuery(<ConnectionsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Outlook" }));
    await waitFor(() => expect(nango.options).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Connect Gmail" })).toBeDisabled();
    onEvent()({ type: "close" });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Connect Gmail" })).toBeEnabled(),
    );
  });

  it("closes the open Connect UI when the page goes away", async () => {
    list.mockResolvedValue([OFF]);
    const { unmount } = renderWithQuery(<ConnectionsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Outlook" }));
    await waitFor(() => expect(nango.options).toHaveLength(1));
    unmount();
    expect(nango.close).toHaveBeenCalledTimes(1);
  });

  it("refetches on connect and shows Connected with the time", async () => {
    list.mockResolvedValueOnce([OFF]);
    renderWithQuery(<ConnectionsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Outlook" }));
    await waitFor(() => expect(nango.options).toHaveLength(1));
    list.mockResolvedValue([
      { integration: "microsoft", connected: true, connected_at: "2026-10-02T09:30:00Z" },
    ]);
    onEvent()({ type: "connect" });
    expect(await screen.findByText(/Outlook — Connected/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Connect Outlook" })).not.toBeInTheDocument();
  });

  it("close only ends the busy state", async () => {
    list.mockResolvedValue([OFF]);
    renderWithQuery(<ConnectionsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Outlook" }));
    await waitFor(() => expect(nango.options).toHaveLength(1));
    onEvent()({ type: "close" });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Connect Outlook" })).toBeEnabled(),
    );
    expect(list).toHaveBeenCalledTimes(1);
  });

  it("an error event shows a plain message", async () => {
    list.mockResolvedValue([OFF]);
    renderWithQuery(<ConnectionsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Outlook" }));
    await waitFor(() => expect(nango.options).toHaveLength(1));
    onEvent()({ type: "error" });
    expect(await screen.findByRole("alert")).toHaveTextContent(/did not connect/i);
  });

  it("shows the problem's detail when the session cannot be made", async () => {
    list.mockResolvedValue([OFF]);
    session.mockRejectedValue(
      new ApiError({
        type: "x",
        title: "Dependency unavailable",
        status: 503,
        detail: "Connections are not set up on this server yet.",
      }),
    );
    renderWithQuery(<ConnectionsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: "Connect Outlook" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Connections are not set up on this server yet.",
    );
    expect(screen.getByRole("button", { name: "Connect Outlook" })).toBeEnabled();
  });

  it("shows the problem's detail when the list fails", async () => {
    list.mockRejectedValue(
      new ApiError({
        type: "x",
        title: "Dependency unavailable",
        status: 503,
        detail: "Connections are not set up on this server yet.",
      }),
    );
    renderWithQuery(<ConnectionsBoard />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Connections are not set up on this server yet.",
    );
  });

  it("an empty list is one plain line, not an error", async () => {
    list.mockResolvedValue([]);
    renderWithQuery(<ConnectionsBoard />);
    expect(
      await screen.findByText("No mail accounts can be connected on this server yet."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("names Gmail and Slack, and shows any other key as it is", async () => {
    list.mockResolvedValue([
      { ...OFF, integration: "google-mail" },
      { ...OFF, integration: "slack" },
      { ...OFF, integration: "zendesk" },
    ]);
    renderWithQuery(<ConnectionsBoard />);
    expect(await screen.findByRole("button", { name: "Connect Gmail" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect Slack" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect zendesk" })).toBeInTheDocument();
  });
});
