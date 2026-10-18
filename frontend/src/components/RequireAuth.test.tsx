import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import RequireAuth from "./RequireAuth";
import { useAuth } from "@/lib/auth";

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

describe("RequireAuth", () => {
  it("shows a loading state and renders no protected content while status is loading", () => {
    vi.mocked(useAuth).mockReturnValue({ status: "loading" } as ReturnType<typeof useAuth>);

    render(
      <RequireAuth>
        <div data-testid="protected">Secret lead data</div>
      </RequireAuth>
    );

    expect(screen.queryByTestId("protected")).toBeNull();
    expect(screen.getByText(/checking your session/i)).not.toBeNull();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("redirects to /login and renders nothing when unauthenticated -- no flash of protected content", () => {
    vi.mocked(useAuth).mockReturnValue({ status: "unauthenticated" } as ReturnType<typeof useAuth>);

    const { container } = render(
      <RequireAuth>
        <div data-testid="protected">Secret lead data</div>
      </RequireAuth>
    );

    expect(screen.queryByTestId("protected")).toBeNull();
    expect(container.innerHTML).toBe("");
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });

  it("renders the protected children once authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({ status: "authenticated" } as ReturnType<typeof useAuth>);

    render(
      <RequireAuth>
        <div data-testid="protected">Secret lead data</div>
      </RequireAuth>
    );

    expect(screen.getByTestId("protected")).not.toBeNull();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
