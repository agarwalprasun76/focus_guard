import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { ApiClientError, authApi, getAuthToken } from "../api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthUser = {
  username: string;
  role: string;
  created_at: string;
};

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    void bootstrapSession();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      login,
      logout,
    }),
    [status, user]
  );

  async function bootstrapSession(): Promise<void> {
    const token = getAuthToken();
    if (!token) {
      setStatus("unauthenticated");
      setUser(null);
      return;
    }

    try {
      const me = await authApi.me();
      setUser(me);
      setStatus("authenticated");
      return;
    } catch (error) {
      if (!(error instanceof ApiClientError) || error.status !== 401) {
        setStatus("unauthenticated");
        setUser(null);
        return;
      }
    }

    try {
      await authApi.refresh(token);
      const me = await authApi.me();
      setUser(me);
      setStatus("authenticated");
    } catch {
      setStatus("unauthenticated");
      setUser(null);
    }
  }

  async function login(username: string, password: string): Promise<void> {
    await authApi.login(username, password);
    const me = await authApi.me();
    setUser(me);
    setStatus("authenticated");
  }

  async function logout(): Promise<void> {
    await authApi.logout();
    setUser(null);
    setStatus("unauthenticated");
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
