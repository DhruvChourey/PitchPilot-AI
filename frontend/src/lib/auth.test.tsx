import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./auth";
import * as api from "./api";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return {
    ...actual, // keep the real ApiError class usable in assertions below
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
  };
});

const mockUser = { id: "u1", email: "a@b.com", is_active: true, email_verified_at: null, created_at: "now" };

/** Exercises the context through real buttons (fireEvent.click), the way
 * an actual component would -- not by reaching into the hook's return
 * value from outside render, which React's rules-of-hooks lint correctly
 * rejects as an impure side effect. */
function Consumer() {
  const { status, user, login, register, logout } = useAuth();
  const [actionError, setActionError] = useState<string | null>(null);

  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="email">{user?.email ?? ""}</span>
      <span data-testid="action-error">{actionError ?? ""}</span>
      <button onClick={() => login("a@b.com", "password123").catch((e) => setActionError((e as Error).message))}>
        do-login
      </button>
      <button onClick={() => register("a@b.com", "password123").catch((e) => setActionError((e as Error).message))}>
        do-register
      </button>
      <button onClick={() => logout().catch(() => {})}>do-logout</button>
    </div>
  );
}

afterEach(() => {
  cleanup(); // RTL doesn't auto-cleanup between tests without `test.globals: true`
  vi.resetAllMocks();
});

describe("AuthProvider initial resolution via /me", () => {
  it("starts in loading, then resolves to authenticated when /me succeeds", async () => {
    vi.mocked(api.me).mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );

    expect(screen.getByTestId("status").textContent).toBe("loading");

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(screen.getByTestId("email").textContent).toBe("a@b.com");
  });

  it("resolves to unauthenticated when /me rejects (no session / 401)", async () => {
    vi.mocked(api.me).mockRejectedValue(new api.ApiError(401, "Not authenticated"));

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
    expect(screen.getByTestId("email").textContent).toBe("");
  });
});

describe("login()", () => {
  it("sets status to authenticated and stores the returned user", async () => {
    vi.mocked(api.me).mockRejectedValue(new api.ApiError(401, "Not authenticated"));
    vi.mocked(api.login).mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

    fireEvent.click(screen.getByText("do-login"));

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(api.login).toHaveBeenCalledWith("a@b.com", "password123");
    expect(screen.getByTestId("email").textContent).toBe("a@b.com");
  });
});

describe("register()", () => {
  it("creates the account then logs in automatically", async () => {
    vi.mocked(api.me).mockRejectedValue(new api.ApiError(401, "Not authenticated"));
    vi.mocked(api.register).mockResolvedValue(mockUser);
    vi.mocked(api.login).mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

    fireEvent.click(screen.getByText("do-register"));

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(api.register).toHaveBeenCalledWith("a@b.com", "password123");
    expect(api.login).toHaveBeenCalledWith("a@b.com", "password123");
  });

  it("surfaces a friendly error and stays unauthenticated if the automatic login step fails", async () => {
    vi.mocked(api.me).mockRejectedValue(new api.ApiError(401, "Not authenticated"));
    vi.mocked(api.register).mockResolvedValue(mockUser);
    vi.mocked(api.login).mockRejectedValue(new api.ApiError(429, "Too many attempts"));

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

    fireEvent.click(screen.getByText("do-register"));

    await waitFor(() => expect(screen.getByTestId("action-error").textContent).toMatch(/account was created/i));
    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
  });
});

describe("logout()", () => {
  it("clears user/status even if the backend call itself fails", async () => {
    vi.mocked(api.me).mockResolvedValue(mockUser);
    vi.mocked(api.logout).mockRejectedValue(new Error("network error"));

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

    fireEvent.click(screen.getByText("do-logout"));

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
    expect(screen.getByTestId("email").textContent).toBe("");
  });
});
