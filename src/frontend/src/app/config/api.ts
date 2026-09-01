export const API_BASE_URL = (import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE_URL ?? "") || "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isUnauthorizedError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

// FastAPI's `detail` field is usually a string, but validation errors (HTTP 422)
// return it as a list of { msg, loc, type, ... } objects instead. Normalize any
// shape down to a human-readable string so callers never end up rendering
// "[object Object]" (e.g. via `new Error(detail)`).
export function extractErrorMessage(errorBody: unknown, status: number): string {
  const detail = (errorBody as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String((item as { msg: unknown }).msg) : null))
      .filter((message): message is string => Boolean(message));
    if (messages.length) return messages.join("; ");
  }
  if (detail && typeof detail === "object" && "msg" in detail) return String((detail as { msg: unknown }).msg);
  return `Request failed with status ${status}`;
}

export type FetchApiOptions = RequestInit & { timeoutMs?: number };

const DEFAULT_REQUEST_TIMEOUT_MS = 30_000;

export async function fetchApi<T>(endpoint: string, options?: FetchApiOptions): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, signal: callerSignal, ...requestOptions } = options ?? {};
  const controller = new AbortController();
  let timedOut = false;
  const onCallerAbort = () => controller.abort();
  if (callerSignal) {
    if (callerSignal.aborted) controller.abort();
    else callerSignal.addEventListener("abort", onCallerAbort, { once: true });
  }
  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  const hasBody = requestOptions.body != null;
  const headers: Record<string, string> = {
    ...(hasBody ? { "Content-Type": "application/json" } : {}),
    ...((requestOptions.headers as Record<string, string> | undefined) ?? {}),
  };
  try {
    const response = await fetch(url, {
      ...requestOptions,
      keepalive: true,
      signal: controller.signal,
      headers,
    } as RequestInit);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      throw new ApiError(extractErrorMessage(errorBody, response.status), response.status);
    }

    return response.json();
  } catch (error) {
    if (timedOut) {
      throw new ApiError("Hệ thống phản hồi quá lâu. Bạn vui lòng thử lại.", 408);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
    callerSignal?.removeEventListener("abort", onCallerAbort);
  }
}
