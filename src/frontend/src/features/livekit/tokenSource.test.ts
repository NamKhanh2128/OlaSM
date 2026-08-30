import { beforeEach, describe, expect, it, vi } from "vitest";

const { endpoint } = vi.hoisted(() => ({ endpoint: vi.fn() }));

vi.mock("livekit-client", () => ({
  TokenSource: { endpoint },
}));

import { createAloSMTokenSource } from "./tokenSource";

describe("createAloSMTokenSource", () => {
  beforeEach(() => {
    localStorage.clear();
    endpoint.mockReset();
  });

  it("rejects unauthenticated LiveKit calls", () => {
    expect(() => createAloSMTokenSource()).toThrow("Vui lòng đăng nhập");
    expect(endpoint).not.toHaveBeenCalled();
  });

  it("sends the app bearer token only to the backend token endpoint", () => {
    localStorage.setItem("alosm_access_token", "access-token");
    endpoint.mockReturnValue({ tokenSource: true });

    expect(createAloSMTokenSource()).toEqual({ tokenSource: true });
    expect(endpoint).toHaveBeenCalledWith("/api/v1/livekit/token", {
      headers: { Authorization: "Bearer access-token" },
    });
  });
});
