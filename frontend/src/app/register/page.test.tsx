import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import RegisterPage from "./page";
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

describe("RegisterPage", () => {
  it("shows field-level validation errors from a 422 (e.g. password too short)", async () => {
    const register = vi
      .fn()
      .mockRejectedValue(
        new ApiError(422, "String should have at least 8 characters", {
          password: "String should have at least 8 characters",
        })
      );
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", register } as unknown as ReturnType<
      typeof useAuth
    >);

    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() =>
      expect(screen.getByText(/string should have at least 8 characters/i)).not.toBeNull()
    );
  });

  it("surfaces the friendly 'created but could not log in automatically' message", async () => {
    const register = vi
      .fn()
      .mockRejectedValue(new Error("Your account was created, but we couldn't log you in automatically. Please log in."));
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated", register } as unknown as ReturnType<
      typeof useAuth
    >);

    render(<RegisterPage />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(screen.getByText(/please log in/i)).not.toBeNull());
  });

  it("redirects to /leads instead of showing the form when already authenticated", async () => {
    vi.mocked(useAuth).mockReturnValue({ status: "authenticated", register: vi.fn() } as unknown as ReturnType<
      typeof useAuth
    >);

    render(<RegisterPage />);

    expect(screen.queryByLabelText(/email/i)).toBeNull();
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/leads"));
  });
});
