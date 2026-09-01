import { beforeEach, describe, expect, it, vi } from "vitest";

const mockEndpoint = vi.hoisted(() => vi.fn());

vi.mock("livekit-client", () => ({
  TokenSource: {
    endpoint: mockEndpoint,
  },
}));

import { createAloSMTokenSource } from "./tokenSource";

describe("createAloSMTokenSource", () => {
  beforeEach(() => {
    localStorage.clear();
    mockEndpoint.mockClear();
  });

  it("rejects unauthenticated LiveKit calls", () => {
    expect(() => createAloSMTokenSource()).toThrow("Vui lòng đăng nhập");
    expect(mockEndpoint).not.toHaveBeenCalled();
  });

  it("sends the app bearer token only to the backend token endpoint", () => {
    const mockResult = { tokenSource: true };
    mockEndpoint.mockReturnValueOnce(mockResult);
    localStorage.setItem("alosm_access_token", "access-token");

    expect(createAloSMTokenSource()).toEqual(mockResult);
    expect(mockEndpoint).toHaveBeenCalledWith("/api/v1/livekit/token", {
      headers: { Authorization: "Bearer access-token" },
    });
  });
});
