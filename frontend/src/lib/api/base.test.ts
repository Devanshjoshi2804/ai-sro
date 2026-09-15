import { describe, expect, it, vi } from "vitest";

async function baseFor(configured: string, pageOrigin: string): Promise<string> {
  vi.resetModules();
  vi.doMock("@/lib/env", () => ({ env: { NEXT_PUBLIC_API_URL: configured } }));
  vi.stubGlobal("window", { location: { origin: pageOrigin } });
  const { apiWebsocketBase } = await import("./base");
  return apiWebsocketBase();
}

describe("the websocket base", () => {
  it("resolves a same-origin path against the page it is on", async () => {
    // What a reverse proxy makes possible, and what `new WebSocket()` refuses
    // to be given directly: it has no scheme to connect with.
    expect(await baseFor("/api", "http://10.11.9.25:8088")).toBe("ws://10.11.9.25:8088/api");
  });

  it("leaves an absolute url absolute", async () => {
    expect(await baseFor("http://10.11.9.25:8000", "http://anywhere")).toBe("ws://10.11.9.25:8000");
  });

  it("carries tls across, so a secure page does not open an insecure socket", async () => {
    expect(await baseFor("/api", "https://sro.example")).toBe("wss://sro.example/api");
  });

  it("does not leave a trailing slash for a path to be appended to", async () => {
    // `new URL("/api", origin)` normalises; the caller appends `/v1/...` and
    // two slashes are a 404 nobody enjoys reading.
    expect(await baseFor("/", "http://host:1")).not.toMatch(/\/$/);
  });
});
