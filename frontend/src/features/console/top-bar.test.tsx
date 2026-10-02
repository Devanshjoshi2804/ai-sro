/**
 * The bar had no test at all, and that is how it lost its tenant label.
 *
 * Phase 6 added five links to it. The bar scrolled as a whole, so the extra
 * width pushed the tenant name and the sign-out button off the right-hand edge
 * at 1512px -- found in a screenshot, not by the suite. That label is the one
 * this file's own comment says has to be right, because it tells somebody which
 * warehouse they are about to write to, and a control you have to go looking
 * for is not on the bar.
 *
 * jsdom has no layout, so none of this can assert pixels. What it can hold is
 * the structural rule that made the overflow safe: the links live in their own
 * scroller, and the tenant group and `right` slot are outside it.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { TopBar, BarGroup, BarLink, MainLinks } from "@/features/console/top-bar";

vi.mock("next/navigation", () => ({ usePathname: () => "/jobs" }));
vi.mock("@/lib/api/credential", () => ({
  whoAmI: vi.fn(() => ({ tenant: "acme" })),
  forget: vi.fn(),
}));

const many = (
  <BarGroup label="Watch">
    {Array.from({ length: 14 }, (_, i) => (
      <BarLink key={i} href={`/page-${i}`}>{`A rather long link label ${i}`}</BarLink>
    ))}
  </BarGroup>
);

describe("TopBar", () => {
  beforeEach(() => vi.clearAllMocks());

  it("keeps the tenant reachable however many links are on the bar", () => {
    render(<TopBar>{many}</TopBar>);
    expect(screen.getByText("acme")).toBeInTheDocument();
    // Its accessible name is its text, not its title attribute.
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
  });

  it("scrolls the links and not the bar, so what sits beside them cannot be pushed off", () => {
    const { container } = render(<TopBar>{many}</TopBar>);
    const bar = container.querySelector('[data-chrome="bar"]') as HTMLElement;
    expect(bar.style.overflow).toBe("hidden");

    // The links' own scroller. `minWidth: 0` is the part that actually lets a
    // flex child shrink instead of forcing its parent wider -- without it the
    // bar grows and the tenant goes over the edge again.
    const scroller = screen.getByText("A rather long link label 0").closest("div")
      ?.parentElement as HTMLElement;
    expect(scroller.style.overflowX).toBe("auto");
    expect(scroller.style.minWidth).toBe("0px");
  });

  it("renders the right-hand slot outside the scroller, beside the tenant", () => {
    render(<TopBar right={<span>$0.8811 of $100.00 today</span>}>{many}</TopBar>);
    const spend = screen.getByText("$0.8811 of $100.00 today");
    expect(spend).toBeInTheDocument();

    // Whatever `right` holds must not have landed inside the scrolling links.
    const scroller = screen.getByText("A rather long link label 0").closest("div")
      ?.parentElement as HTMLElement;
    expect(scroller.contains(spend)).toBe(false);
  });

  it("says the tenant is unknown rather than naming the wrong one", async () => {
    const credential = await import("@/lib/api/credential");
    vi.mocked(credential.whoAmI).mockReturnValueOnce(null as never);
    render(<TopBar>{many}</TopBar>);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("MainLinks is the one list both bars render, Connections included", () => {
    render(
      <TopBar>
        <MainLinks />
      </TopBar>,
    );
    const names = screen.getAllByRole("link").map((l) => l.textContent);
    expect(names.slice(1)).toEqual([
      "Threads",
      "What we know",
      "Triggers",
      "Connections",
      "Overview",
    ]);
  });
});
