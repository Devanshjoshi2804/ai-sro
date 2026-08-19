import { afterEach, describe, expect, it } from "vitest";
import { forget, remember, usableCredential, whoAmI } from "@/lib/api/credential";

/**
 * The credential this browser acts with. Nothing here checks a signature --
 * the backend does that on every request -- but a token this browser cannot
 * use should not be presented as though it could, and nothing was reading the
 * expiry at all: a token that ran out overnight left the console loading
 * normally and failing on every single request with no way to see why.
 */
function token(claims: Record<string, unknown>): string {
  const payload = btoa(JSON.stringify(claims)).replace(/=+$/, "");
  return `header.${payload}.signature`;
}

const HOUR = 3600;
const now = () => Math.floor(Date.now() / 1000);

afterEach(() => forget());

describe("a held credential", () => {
  it("is usable while it is still in date", () => {
    remember(token({ ten: "acme", sub: "clerk", exp: now() + HOUR }));

    expect(usableCredential()).not.toBeNull();
  });

  it("is not usable once it has expired", () => {
    remember(token({ ten: "acme", sub: "clerk", exp: now() - HOUR }));

    expect(usableCredential()).toBeNull();
  });

  it("is taken at face value when it says nothing about expiry", () => {
    remember(token({ ten: "acme", sub: "clerk" }));

    expect(usableCredential()).not.toBeNull();
  });

  it("names who is acting, for the label only", () => {
    remember(token({ ten: "acme", sub: "clerk@acme.test", exp: now() + HOUR }));

    expect(whoAmI()).toEqual({ tenant: "acme", principal: "clerk@acme.test" });
  });

  it("says nothing at all rather than guessing at a token it cannot read", () => {
    remember("not-a-token");

    expect(whoAmI()).toBeNull();
  });

  it("is gone after it is forgotten", () => {
    remember(token({ ten: "acme", sub: "clerk", exp: now() + HOUR }));

    forget();

    expect(usableCredential()).toBeNull();
  });
});
