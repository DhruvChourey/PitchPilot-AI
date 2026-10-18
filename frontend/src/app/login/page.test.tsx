import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("LoginPage", () => {
  it("shows a loading state instead of the form while the session check is in flight", () => {
    vi.mocked(useAuth).mockReturnValue({ status: "loading", login: vi.fn() } as unknown as ReturnType<
      typeof useAuth
    >);

    render(<LoginPage />);

    expect(screen.queryByLabelText(/email/i)).toBeNull();
    expect(screen.getByText(/checking your session/i)).not.toBeNull();
  });

  it("redirects to /leads instead of showing the form when already authenticated", async () => {
    vi.mocked(useAuth).mockReturnValue({ status: "authenticated", login: vi.fn() } as unknown as ReturnType<
      typeof useAuth
    >);

    render(<LoginPage />);

    expect(screen.queryByLabelText(/email/i)).toBeNull();
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/leads"));
  });

  it("submits the trimmed email and password to login()", async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", login } as unknown as ReturnType<typeof useAuth>);

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "  a@b.com  " } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "correct-horse-1" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => expect(login).toHaveBeenCalledWith("a@b.com", "correct-horse-1"));
  });

  it("shows a friendly error message from a failed login without a second request while the first is in flight", async () => {
    let resolveLogin: () => void = () => {};
    const login = vi.fn().mockImplementation(
      () =>
        new Promise<void>((resolve, reject) => {
          resolveLogin = () => reject(new ApiError(401, "Invalid email or password"));
        })
    );
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", login } as unknown as ReturnType<typeof useAuth>);

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "wrong-password" } });

    const submitButton = screen.getByRole("button", { name: /log in/i });
    fireEvent.click(submitButton);
    // A second click while the first submit is still pending must not
    // fire a second call -- this is the "no duplicate submissions" guard.
    fireEvent.click(submitButton);
    expect(login).toHaveBeenCalledTimes(1);

    resolveLogin();

    await waitFor(() => expect(screen.getByText(/invalid email or password/i)).not.toBeNull());
  });
});
