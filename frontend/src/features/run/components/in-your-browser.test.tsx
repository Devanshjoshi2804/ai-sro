import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { InYourBrowser, whereItIsActing } from "@/features/run/components/in-your-browser";
import type { RunStep } from "@/features/run/stream";

/**
 * The screen for a run happening in somebody's own browser.
 *
 * The `waiting` payload is not covered by OpenAPI — the stream is a
 * `StreamingResponse`, so its shape is hand-written on both sides. That is why
 * the router asserts it too: a double that implements the thing under test
 * proves the double.
 */
function step(over: Partial<RunStep> = {}): RunStep {
  return {
    index: 0,
    medium: "ui",
    disposition: "performed",
    intent: "Open the areas page",
    method: null,
    url: "https://wms.acme.test/areas",
    status_code: null,
    request_body: null,
    matched_by: null,
    detail: null,
    iteration: null,
    ...over,
  } as RunStep;
}

describe("watching a run in your own browser", () => {
  it("says the machine is holding back while you type, and for how long", () => {
    // The one state that shows the system deferring to the person. Without it a
    // held run is indistinguishable from a stalled one.
    render(
      <InYourBrowser
        steps={[step()]}
        waiting={{ index: 1, heldMs: 2500 }}
        of={8}
        where="wms.acme.test"
        browser="Lena's laptop"
        finished={false}
      />,
    );

    expect(screen.getByText(/held — you are typing/i)).toBeInTheDocument();
    expect(screen.getByText(/or the moment you stop/i)).toBeInTheDocument();
  });

  it("says nothing about holding back when nobody is typing", () => {
    render(
      <InYourBrowser
        steps={[step()]}
        waiting={null}
        of={8}
        where="wms.acme.test"
        browser={null}
        finished={false}
      />,
    );

    expect(screen.queryByText(/held/i)).not.toBeInTheDocument();
  });

  it("names where it is acting and which step of how many", () => {
    // A run may act in a tab the operator is not looking at. Unnamed, that is
    // indistinguishable from something that should not be trusted with it.
    render(
      <InYourBrowser
        steps={[step(), step({ index: 1 })]}
        waiting={null}
        of={8}
        where="wms.acme.test"
        browser="Lena's laptop"
        finished={false}
      />,
    );

    expect(screen.getByText(/step 2 of 8/i)).toBeInTheDocument();
    expect(screen.getByText(/on wms\.acme\.test/i)).toBeInTheDocument();
    expect(screen.getByText("Lena's laptop")).toBeInTheDocument();
  });

  it("never promises a screen it does not keep", () => {
    // A run keeps no screenshots by a written decision. Saying so is better
    // than a blank panel implying a feed that is not coming.
    render(
      <InYourBrowser
        steps={[step()]}
        waiting={null}
        of={null}
        where={null}
        browser={null}
        finished={false}
      />,
    );

    expect(screen.getByText(/no screen is kept/i)).toBeInTheDocument();
  });

  it("shows the write a shadow run produced and did not send", () => {
    render(
      <InYourBrowser
        steps={[step({ disposition: "withheld", request_body: '{"name":"THREE TE"}' })]}
        waiting={null}
        of={1}
        where="wms.acme.test"
        browser={null}
        finished
      />,
    );

    expect(screen.getByText(/withheld: \{"name":"THREE TE"\}/i)).toBeInTheDocument();
  });

  it("tells a refusal to take your screen apart from a control it could not find", () => {
    // Both arrive as a failed gesture with a sentence. Only the kind separates
    // a system behaving well from one that could not do the work.
    render(
      <InYourBrowser
        steps={[
          step({
            disposition: "failed",
            detail: "focus_not_permitted: the run may not take the screen",
          }),
        ]}
        waiting={null}
        of={1}
        where="wms.acme.test"
        browser={null}
        finished
      />,
    );

    expect(screen.getByText(/did not bring the tab to the front/i)).toBeInTheDocument();
  });

  it("shows how a control was found, which is what makes it a replay", () => {
    render(
      <InYourBrowser
        steps={[step({ matched_by: "label" })]}
        waiting={null}
        of={1}
        where="wms.acme.test"
        browser={null}
        finished
      />,
    );

    expect(screen.getByText(/by label/i)).toBeInTheDocument();
  });
});

describe("where a run is acting", () => {
  it("takes the last step that named a page, not the first", () => {
    // A run navigates. The page it is on now is the one worth naming.
    expect(
      whereItIsActing([
        step({ url: "https://wms.acme.test/areas" }),
        step({ index: 1, url: "https://wms.acme.test/areas/new" }),
      ]),
    ).toBe("wms.acme.test");
  });

  it("says nothing rather than guessing when no step named a page", () => {
    // Every step of a network run has a url; a UI run's steps only recently do.
    expect(whereItIsActing([step({ url: null })])).toBeNull();
  });
});
