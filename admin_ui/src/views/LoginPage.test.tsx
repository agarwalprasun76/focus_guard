import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { LoginPage } from "./LoginPage";

const loginMock = vi.fn(async (_username: string, _password: string) => undefined);

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({ login: loginMock }),
}));

describe("LoginPage", () => {
  function renderPage() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  it("submits username and password via form", async () => {
    loginMock.mockResolvedValueOnce(undefined);
    renderPage();

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Admin Password"), { target: { value: "secret123" } });
    fireEvent.submit(screen.getByRole("button", { name: "Continue" }).closest("form") as HTMLFormElement);

    await waitFor(() => expect(loginMock).toHaveBeenCalledWith("admin", "secret123"));
  });

  it("announces login errors", async () => {
    loginMock.mockRejectedValueOnce(new Error("bad creds"));
    renderPage();

    fireEvent.change(screen.getByLabelText("Admin Password"), { target: { value: "wrong" } });
    fireEvent.submit(screen.getByRole("button", { name: "Continue" }).closest("form") as HTMLFormElement);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
