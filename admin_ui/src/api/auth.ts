import { requestJson } from "./client";
import { clearAuthToken, setAuthToken } from "./token";

type AuthTokenResponse = {
  token: string;
  expires_at: string;
  role: string;
};

type AuthMeResponse = {
  username: string;
  role: string;
  created_at: string;
};

export async function login(username: string, password: string): Promise<AuthTokenResponse> {
  const payload = await requestJson<AuthTokenResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
    skipAuth: true,
  });
  setAuthToken(payload.token);
  return payload;
}

export async function refresh(token: string): Promise<AuthTokenResponse> {
  const payload = await requestJson<AuthTokenResponse>("/auth/refresh", {
    method: "POST",
    body: { token },
    skipAuth: true,
  });
  setAuthToken(payload.token);
  return payload;
}

export async function me(): Promise<AuthMeResponse> {
  return requestJson<AuthMeResponse>("/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await requestJson<{ success: boolean }>("/auth/logout", { method: "POST" });
  } finally {
    clearAuthToken();
  }
}
