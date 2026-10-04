import { beforeEach, describe, expect, it, vi } from "vitest";

const mockEndpoint = vi.hoisted(() => vi.fn());

vi.mock("livekit-client", () => ({
  TokenSource: {
    endpoint: mockEndpoint,
  },
}));

import { createOlaSMTokenSource, createAloSMTokenSource } from "./tokenSource";

describe("createOlaSMTokenSource", () => {
  beforeEach(() => {
    localStorage.clear();
    mockEndpoint.mockClear();
  });

  it("rejects unauthenticated LiveKit calls", () => {
    expect(() => createOlaSMTokenSource()).toThrow("Vui lòng đăng nhập");
    expect(mockEndpoint).not.toHaveBeenCalled();
  });

  it("sends the app bearer token only to the backend token endpoint", () => {
    const mockResult = { tokenSource: true };
    mockEndpoint.mockReturnValueOnce(mockResult);
    localStorage.setItem("olasm_access_token", "access-token");

    expect(createOlaSMTokenSource()).toEqual(mockResult);
    expect(createAloSMTokenSource()).toEqual(mockResult);
    expect(mockEndpoint).toHaveBeenCalledWith("/api/v1/livekit/token", {
      headers: { Authorization: "Bearer access-token" },
    });
  });
});
