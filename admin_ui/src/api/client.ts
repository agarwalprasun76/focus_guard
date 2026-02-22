import { clearAuthToken, getAuthToken } from "./token";

export type ApiErrorCode =
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "VALIDATION_ERROR"
  | "NOT_FOUND"
  | "CONFLICT"
  | "DEVICE_OFFLINE"
  | "UPSTREAM_ERROR"
  | "INTERNAL_ERROR";

export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown>;
  readonly retryAfterSeconds?: number;
  readonly requestId?: string;

  constructor(params: {
    status: number;
    code: string;
    message: string;
    details?: Record<string, unknown>;
    retryAfterSeconds?: number;
    requestId?: string;
  }) {
    super(params.message);
    this.name = "ApiClientError";
    this.status = params.status;
    this.code = params.code;
    this.details = params.details;
    this.retryAfterSeconds = params.retryAfterSeconds;
    this.requestId = params.requestId;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  headers?: HeadersInit;
  skipAuth?: boolean;
};

const API_BASE_URL = import.meta.env.VITE_ADMIN_API_BASE_URL ?? "/admin/api/v1";

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", createRequestId());
  }

  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAuthToken();
  if (token && !options.skipAuth) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    const error = extractError(response.status, payload, response.headers);
    if (error.status === 401 && !options.skipAuth) {
      clearAuthToken();
    }
    throw error;
  }

  return payload as T;
}

function extractError(status: number, payload: unknown, responseHeaders?: Headers): ApiClientError {
  const requestIdFromHeader = responseHeaders?.get("x-request-id") ?? undefined;
  if (isObject(payload) && isObject(payload.error)) {
    const err = payload.error;
    const details = isObject(err.details) ? err.details : undefined;
    const requestIdFromDetails =
      details && typeof details.request_id === "string" ? details.request_id : undefined;
    return new ApiClientError({
      status,
      code: asString(err.code, fallbackCode(status)),
      message: asString(err.message, "Request failed"),
      details,
      retryAfterSeconds:
        typeof err.retry_after_seconds === "number" ? err.retry_after_seconds : undefined,
      requestId: requestIdFromDetails ?? requestIdFromHeader,
    });
  }

  if (isObject(payload) && typeof payload.detail === "string") {
    return new ApiClientError({
      status,
      code: fallbackCode(status),
      message: payload.detail,
    });
  }

  return new ApiClientError({
    status,
    code: fallbackCode(status),
    message: typeof payload === "string" ? payload : "Request failed",
    requestId: requestIdFromHeader,
  });
}

function fallbackCode(status: number): ApiErrorCode {
  if (status === 400) return "VALIDATION_ERROR";
  if (status === 401) return "UNAUTHORIZED";
  if (status === 403) return "FORBIDDEN";
  if (status === 404) return "NOT_FOUND";
  if (status === 409) return "CONFLICT";
  if (status === 502) return "UPSTREAM_ERROR";
  return "INTERNAL_ERROR";
}

function asString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

function isObject(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null;
}

function createRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
