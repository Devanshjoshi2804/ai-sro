import { describe, expect, it, vi, afterEach } from "vitest";
import { ApiError, api } from "@/lib/api/client";

/**
 * An error body is data crossing a trust boundary. This crashed a page: a
 * framework's validation errors came back as a list of objects, and `detail`
 * reached React as a child.
 */
function answering(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      statusText: "Unprocessable Content",
      json: async () => body,
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("ApiError", () => {
  it("renders a framework's list of validation objects as words", async () => {
    answering(422, {
      detail: [
        {
          type: "model_attributes_type",
          loc: ["body", "objective_key"],
          msg: "Input should be a valid dictionary",
        },
      ],
    });

    const error = (await api.get("/v1/anything").catch((cause) => cause)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.problem.detail).toBe("objective_key: Input should be a valid dictionary");
    expect(typeof error.problem.detail).toBe("string");
  });

  it("keeps a proper problem document as it is", async () => {
    answering(409, {
      type: "https://ai-sro.dev/problems/refused",
      title: "Conflict",
      status: 409,
      detail: "3 runs against this system have failed",
    });

    const error = (await api.get("/v1/anything").catch((cause) => cause)) as ApiError;

    expect(error.problem.detail).toBe("3 runs against this system have failed");
    expect(error.problem.status).toBe(409);
  });

  it("says something useful when the body is not JSON at all", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        statusText: "Bad Gateway",
        json: async () => {
          throw new Error("not json");
        },
      }),
    );

    const error = (await api.get("/v1/anything").catch((cause) => cause)) as ApiError;

    expect(error.problem.detail).toContain("/v1/anything");
    expect(error.problem.status).toBe(502);
  });
});
