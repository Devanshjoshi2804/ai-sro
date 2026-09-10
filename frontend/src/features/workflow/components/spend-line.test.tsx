/**
 * The one place a person reads the bill. The harm it can do is say a day was
 * cheap when its calls were never priced — which is what a total alone says.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithQuery } from "@/test/render";
import { SpendLine, SpendPage } from "@/features/workflow/components/spend-line";
import * as workflowApi from "@/features/workflow/api";

describe("SpendLine", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("puts the day against its cap", async () => {
    vi.spyOn(workflowApi, "readSpend").mockResolvedValue({
      cost_usd: 0.881104,
      unpriced: 0,
      cap_usd: 100,
    } as never);
    renderWithQuery(<SpendLine />);
    expect(await screen.findByText("$0.8811 of $100.00 today")).toBeInTheDocument();
  });

  it("marks a day whose calls could not be priced", async () => {
    vi.spyOn(workflowApi, "readSpend").mockResolvedValue({
      cost_usd: 0,
      unpriced: 2,
      cap_usd: 100,
    } as never);
    renderWithQuery(<SpendLine />);
    const line = await screen.findByText("$0.0000 of $100.00 today · 2 unpriced");
    expect(line).toHaveAttribute("data-over-cap", "true");
  });

  it("says nothing at all rather than a wrong number when the door is shut", async () => {
    vi.spyOn(workflowApi, "readSpend").mockRejectedValue(new Error("nope"));
    const { container } = renderWithQuery(<SpendLine />);
    await new Promise((r) => setTimeout(r, 0));
    expect(container.textContent).not.toContain("$");
  });
});

describe("SpendPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("names the cap the deployment configured", async () => {
    vi.spyOn(workflowApi, "readSpend").mockResolvedValue({
      cost_usd: 3.5,
      unpriced: 0,
      cap_usd: 10,
    } as never);
    renderWithQuery(<SpendPage />);
    expect(await screen.findByText("$3.5000 of $10.00 today")).toBeInTheDocument();
  });
});
