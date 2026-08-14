import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BatchCard } from "@/features/console/batch-card";
import * as runApi from "@/features/run/api";

/**
 * The last thing between a sentence and several real writes. What it must
 * never do is make six writes look like one confirmation nobody read.
 */
function renderCard(props: Partial<Parameters<typeof BatchCard>[0]> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <BatchCard
        skillId="skl-1"
        skillName="Adjust LPN quantity"
        items={[
          { query: "LPN-1", quantity: "48" },
          { query: "LPN-2", quantity: "65" },
        ]}
        runnable
        {...props}
      />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("BatchCard", () => {
  it("shows every value that would be written, before anything is sent", () => {
    renderCard();

    expect(screen.getByText("LPN-1")).toBeInTheDocument();
    expect(screen.getByText("48")).toBeInTheDocument();
    expect(screen.getByText("LPN-2")).toBeInTheDocument();
    expect(screen.getByText(/nothing sent yet/)).toBeInTheDocument();
  });

  it("sends only what the operator confirmed", async () => {
    const batch = vi.spyOn(runApi, "runBatch").mockResolvedValue({
      items: [
        { parameters: {}, run_id: "run-1", status: "succeeded", detail: null },
        { parameters: {}, run_id: "run-2", status: "succeeded", detail: null },
      ],
      performed: 2,
      stopped_early: null,
    } as never);

    renderCard();
    await userEvent.click(screen.getByRole("button", { name: /run 2/i }));

    await waitFor(() => expect(batch).toHaveBeenCalledOnce());
    expect(batch.mock.calls[0][1]).toEqual([
      { query: "LPN-1", quantity: "48" },
      { query: "LPN-2", quantity: "65" },
    ]);
  });

  it("says which items were not attempted when a limit stopped the batch", async () => {
    vi.spyOn(runApi, "runBatch").mockResolvedValue({
      items: [{ parameters: {}, run_id: "run-1", status: "failed", detail: "500" }],
      performed: 0,
      stopped_early: "3 runs against this system have failed in the last 15 minutes",
    } as never);

    renderCard();
    await userEvent.click(screen.getByRole("button", { name: /run 2/i }));

    expect(await screen.findByText(/Stopped before the rest/)).toBeInTheDocument();
    expect(screen.getByText(/waiting/)).toBeInTheDocument();
  });

  it("refuses to run a skill nobody has reviewed", () => {
    renderCard({ runnable: false });

    expect(screen.getByRole("button", { name: /run 2/i })).toBeDisabled();
  });
});
