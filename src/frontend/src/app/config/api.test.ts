import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchApi } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchApi", () => {
  it("returns a successful JSON response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchApi<{ status: string }>("/health")).resolves.toEqual({ status: "ok" });
  });

  it("normalizes FastAPI validation errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: [{ msg: "Số điện thoại không hợp lệ" }] }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const request = fetchApi("/auth/register");
    await expect(request).rejects.toEqual(
      expect.objectContaining({
        name: "ApiError",
        status: 422,
        message: "Số điện thoại không hợp lệ",
      }),
    );
  });
});
