import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataView } from "@/components/data-view";

/**
 * The furniture every list needed and none of them had.
 *
 * The states asserted here are the ones the lists each got wrong in a different
 * way: an empty table rendered on a failed request, an empty state written as a
 * sentence in a table cell, and no way at all to find one row among fifty that
 * render identically.
 */
type Row = { id: string; name: string; status: string };

const rows: Row[] = [
  { id: "1", name: "Create a work area", status: "sealed" },
  { id: "2", name: "Create a work area", status: "sealed" },
  { id: "3", name: "Reprint a label", status: "abandoned" },
];

function show(over: Partial<Parameters<typeof DataView<Row>>[0]> = {}) {
  return render(
    <DataView<Row>
      title="Recordings"
      loading={false}
      error={null}
      rows={rows}
      matches={(row, term) => row.name.toLowerCase().includes(term)}
      facet={{ name: "status", of: (row) => row.status }}
      empty={{ line: "No recordings yet.", hint: "Teach a workflow to make the first." }}
      {...over}
    >
      {(shown) => (
        <ul>
          {shown.map((row) => (
            <li key={row.id}>{row.name}</li>
          ))}
        </ul>
      )}
    </DataView>,
  );
}

describe("the list shell", () => {
  it("says a request failed rather than rendering an empty list", () => {
    // An empty table on a failed request makes the claim "there are none of
    // these", which is a different and much worse thing to tell somebody.
    show({ error: new Error("503 service unavailable") });

    expect(screen.getByText(/could not be read/i)).toBeInTheDocument();
    expect(screen.getByText(/503 service unavailable/)).toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("gives an empty list somewhere to go, not a sentence in a cell", () => {
    show({ rows: [] });

    expect(screen.getByText("No recordings yet.")).toBeInTheDocument();
    expect(screen.getByText(/teach a workflow/i)).toBeInTheDocument();
  });

  it("narrows to what was searched for, and says how much of the whole that is", async () => {
    show();
    expect(screen.getAllByRole("listitem")).toHaveLength(3);

    await userEvent.type(screen.getByLabelText(/search recordings/i), "reprint");

    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("1 of 3")).toBeInTheDocument();
  });

  it("offers a way back when a search matches nothing", async () => {
    // A blank screen with a search box above it is indistinguishable from a
    // list that is genuinely empty.
    show();
    await userEvent.type(screen.getByLabelText(/search recordings/i), "nothing like this");

    expect(screen.getByText(/nothing here matches that/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /clear the search/i }));

    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("builds its filters from the values actually present, with counts", async () => {
    // Not from a list registered here: a status nothing has is never offered,
    // and a new one never has to be added in two places.
    show();

    const sealed = screen.getByRole("button", { name: /sealed 2/i });
    expect(screen.getByRole("button", { name: /abandoned 1/i })).toBeInTheDocument();

    await userEvent.click(sealed);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(sealed).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(sealed);
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("offers no filter when everything has the same value", () => {
    // One chip that selects everything is a control that does nothing.
    show({ rows: [rows[0], rows[1]] });

    expect(screen.queryByRole("button", { name: /sealed/i })).not.toBeInTheDocument();
  });

  it("hides the search box for a list that does not want one", () => {
    show({ matches: undefined });

    expect(screen.queryByLabelText(/search/i)).not.toBeInTheDocument();
  });

  it("shows no count while it is still loading", () => {
    // A count rendered before the answer arrives is a number somebody reads as
    // real. Zero of anything is a claim.
    show({ loading: true });

    expect(screen.queryByText(/of 3/)).not.toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });
});
