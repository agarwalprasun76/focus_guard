import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { ApiClientError } from "../api";
import { useAuth } from "../auth/AuthProvider";

export function LoginPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const redirectTo =
    typeof location.state === "object" && location.state && "from" in location.state
      ? String((location.state as { from?: string }).from ?? "/")
      : "/";

  const loginMutation = useMutation({
    mutationFn: () => login(username.trim(), password),
    onSuccess: () => {
      navigate(redirectTo, { replace: true });
    },
  });

  const errorMessage =
    loginMutation.error instanceof ApiClientError
      ? loginMutation.error.message
      : loginMutation.error
        ? "Unable to sign in"
        : null;

  return (
    <main className="grid min-h-screen place-items-center px-4">
      <form
        className="w-full max-w-md rounded-2xl border border-slate-300/80 bg-white/90 p-6 shadow-lg backdrop-blur"
        onSubmit={(event) => {
          event.preventDefault();
          if (!loginMutation.isPending && password.trim().length > 0) {
            loginMutation.mutate();
          }
        }}
        aria-describedby="login-help"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ocean">FocusGuard Admin</p>
        <h1 className="mt-2 font-display text-2xl text-ink">Sign in</h1>
        <p id="login-help" className="mt-1 text-sm text-gray-700">Use your admin credentials to access the dashboard.</p>

        <label className="mt-5 block text-sm font-medium text-gray-700" htmlFor="username">
          Username
        </label>
        <input
          id="username"
          type="text"
          className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="admin"
          autoComplete="username"
          required
        />

        <label className="mt-4 block text-sm font-medium text-gray-700" htmlFor="password">
          Admin Password
        </label>
        <input
          id="password"
          type="password"
          className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Enter password"
          autoComplete="current-password"
          required
          aria-invalid={Boolean(errorMessage)}
          aria-describedby={errorMessage ? "login-error" : undefined}
        />

        {errorMessage ? <p id="login-error" role="alert" className="mt-3 text-sm text-red-700">{errorMessage}</p> : null}

        <button
          type="submit"
          className="mt-4 w-full rounded-lg bg-ocean px-3 py-2 font-semibold text-white hover:bg-teal-700"
          disabled={loginMutation.isPending}
          aria-busy={loginMutation.isPending}
        >
          {loginMutation.isPending ? "Signing in..." : "Continue"}
        </button>
      </form>
    </main>
  );
}
