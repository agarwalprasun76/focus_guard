import { requestJson } from "./client";

export type ExceptionType = "temporary" | "permanent" | "budgeted" | "block";

export type CreateExceptionInput = {
  domain: string;
  type: ExceptionType;
  reason?: string;
  emergency?: boolean;
  duration_seconds?: number;
  budget_seconds_per_day?: number;
};

export type CreateExceptionResponse = {
  id: string;
  status: string;
  type: string;
  domain: string;
  expires_at: string | null;
  audit_event_id: string | null;
  message?: string;
};

export type ExceptionListItem = {
  id: string;
  domain: string;
  type: string;
  status: string;
  created_at: string | null;
  expires_at: string | null;
  remaining_seconds: number;
  reason: string | null;
  emergency: boolean;
};

export type ListExceptionsResponse = {
  exceptions: ExceptionListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type ListExceptionsParams = {
  status?: "all" | "active" | "expired" | "revoked";
  domain?: string;
  limit?: number;
  offset?: number;
};

export function createException(input: CreateExceptionInput): Promise<CreateExceptionResponse> {
  const payload: Record<string, unknown> = {
    domain: input.domain.trim().toLowerCase(),
    type: input.type,
    reason: input.reason?.trim() || undefined,
    emergency: Boolean(input.emergency),
  };

  if (input.type === "temporary") {
    payload.duration_seconds = input.duration_seconds;
  }

  if (input.type === "budgeted") {
    payload.budget_seconds_per_day = input.budget_seconds_per_day;
  }

  return requestJson<CreateExceptionResponse>("/exceptions", {
    method: "POST",
    body: payload,
  });
}

export function listExceptions(params: ListExceptionsParams = {}): Promise<ListExceptionsResponse> {
  const query = new URLSearchParams();
  query.set("status", params.status ?? "active");
  query.set("limit", String(params.limit ?? 50));
  query.set("offset", String(params.offset ?? 0));
  if (params.domain) {
    query.set("domain", params.domain.trim().toLowerCase());
  }
  return requestJson<ListExceptionsResponse>(`/exceptions?${query.toString()}`);
}

export function revokeException(exceptionId: string): Promise<{ revoked: boolean; id: string }> {
  return requestJson<{ revoked: boolean; id: string }>(`/exceptions/${encodeURIComponent(exceptionId)}`, {
    method: "DELETE",
  });
}
