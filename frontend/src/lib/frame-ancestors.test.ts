/**
 * The header that decides who may frame the console.
 *
 * Written because the console sent no framing header at all until the side
 * panel needed one: any site could put it in an iframe, and the panel's
 * credential handoff is only as good as the list of origins allowed to be on
 * the other end of it.
 */

import { describe, expect, it } from "vitest";
import { frameAncestors } from "@/lib/frame-ancestors";

const PANEL = "chrome-extension://abcdefghijklmnopabcdefghijklmnop";

describe("frame-ancestors", () => {
  it("allows the extension origins this deployment configured", () => {
    expect(frameAncestors(PANEL)).toBe(`'self' ${PANEL}`);
  });

  it("allows several, since an unpacked build and a packed one differ", () => {
    expect(frameAncestors(`${PANEL}, chrome-extension://second`)).toBe(
      `'self' ${PANEL} chrome-extension://second`,
    );
  });

  it("allows nobody but this site when nothing is configured", () => {
    // The default a deployment gets without knowing this exists, and the reason
    // the header is worth adding even where the panel is never used.
    expect(frameAncestors(undefined)).toBe("'self'");
    expect(frameAncestors("")).toBe("'self'");
    expect(frameAncestors("  ,  ")).toBe("'self'");
  });
});
