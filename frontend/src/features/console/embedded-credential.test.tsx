/**
 * Handing a credential between origins is either exactly right or a hole.
 *
 * The console keeps its token in localStorage, Chrome partitions storage for
 * framed contexts, so the extension's side panel has to hand its token to the
 * console it frames. Everything below is about the refusals rather than the
 * feature: a console that accepts a token from the wrong origin, or accepts one
 * while open in an ordinary tab, is a credential injector reachable by any page
 * that can load it.
 */

import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EmbeddedCredential } from "@/features/console/embedded-credential";
import { credential, forget } from "@/lib/api/credential";

const PANEL = "chrome-extension://abcdefghijklmnopabcdefghijklmnop";
const SOMEWHERE_ELSE = "https://not-the-panel.example";
const TOKEN = "header.payload.signature";

vi.mock("@/lib/env", () => ({
  get env() {
    return { NEXT_PUBLIC_EXTENSION_ORIGINS: origins, NEXT_PUBLIC_API_URL: "http://localhost:8000" };
  },
}));

let origins = PANEL;

/** A message as the browser delivers it, with a `source` that records what was
 * posted back so a test can tell "accepted" from "ignored in silence". */
function arrive(origin: string, data: unknown): ReturnType<typeof vi.fn> {
  const replies = vi.fn();
  const event = new MessageEvent("message", { data, origin });
  // `source` is getter-only on a real MessageEvent, so it is defined onto the
  // instance rather than assigned -- the same shape the browser delivers.
  Object.defineProperty(event, "source", {
    value: { postMessage: replies } as unknown as MessageEventSource,
  });
  window.dispatchEvent(event);
  return replies;
}

/** jsdom has no frames, so being framed is something a test states. */
function framed(is: boolean): void {
  vi.spyOn(window, "top", "get").mockReturnValue(
    (is ? ({} as Window) : window) as Window & typeof globalThis,
  );
}

beforeEach(() => {
  origins = PANEL;
  forget();
});

afterEach(() => {
  vi.restoreAllMocks();
  forget();
});

describe("a console inside the extension's panel", () => {
  it("takes the credential the panel hands it, and says that it did", () => {
    framed(true);
    render(<EmbeddedCredential />);

    const replies = arrive(PANEL, { kind: "sro.credential", token: TOKEN });

    expect(credential()).toBe(TOKEN);
    expect(replies).toHaveBeenCalledWith({ kind: "sro.credential.ok" }, { targetOrigin: PANEL });
  });

  it("ignores a credential from any other origin, without saying so", () => {
    framed(true);
    render(<EmbeddedCredential />);

    const replies = arrive(SOMEWHERE_ELSE, { kind: "sro.credential", token: TOKEN });

    expect(credential()).toBeNull();
    // Silence rather than a refusal: an answer would tell a prober what this
    // console accepts.
    expect(replies).not.toHaveBeenCalled();
  });

  it("ignores anything that is not shaped like a credential", () => {
    framed(true);
    render(<EmbeddedCredential />);

    arrive(PANEL, { kind: "sro.credential", token: "not-a-token" });

    // `remember` validates nothing on its own, so this is the only check.
    expect(credential()).toBeNull();
  });
});

describe("the half that starts the handshake", () => {
  it("announces itself to the panel once it is listening", () => {
    // The whole handshake hangs on this. The iframe's `load` fires when the
    // document is parsed and this listener is registered after hydration, so a
    // panel that posted on load would speak before anyone could hear it -- and
    // the console would sit on its sign-in screen forever while the panel
    // blamed the allowlist.
    framed(true);
    const parent = { postMessage: vi.fn() };
    vi.spyOn(window, "parent", "get").mockReturnValue(parent as unknown as Window);

    render(<EmbeddedCredential />);

    expect(parent.postMessage).toHaveBeenCalledWith({ kind: "sro.ready" }, PANEL);
  });

  it("says nothing to a page that is not an allowed extension", () => {
    origins = "";
    framed(true);
    const parent = { postMessage: vi.fn() };
    vi.spyOn(window, "parent", "get").mockReturnValue(parent as unknown as Window);

    render(<EmbeddedCredential />);

    expect(parent.postMessage).not.toHaveBeenCalled();
  });
});

describe("a console open in an ordinary tab", () => {
  it("cannot be handed a credential at all", () => {
    framed(false);
    render(<EmbeddedCredential />);

    const replies = arrive(PANEL, { kind: "sro.credential", token: TOKEN });

    // Not merely refused -- no listener was ever registered, so the capability
    // does not exist outside a frame.
    expect(credential()).toBeNull();
    expect(replies).not.toHaveBeenCalled();
  });
});

describe("a deployment that has not configured the panel", () => {
  it("accepts nothing, which is the default nobody has to remember", () => {
    origins = "";
    framed(true);
    render(<EmbeddedCredential />);

    arrive(PANEL, { kind: "sro.credential", token: TOKEN });

    expect(credential()).toBeNull();
  });
});
