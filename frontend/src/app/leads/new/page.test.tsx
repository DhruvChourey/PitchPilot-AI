import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import NewLeadPage from "./page";
import { createLead, ApiError } from "@/lib/api";
import { useRedirectOnUnauthorized } from "@/lib/auth";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, createLead: vi.fn() };
});

vi.mock("@/lib/auth", () => ({
  useRedirectOnUnauthorized: vi.fn(),
}));

function fillRequiredField() {
  fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: "Acme Co" } });
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("NewLeadPage", () => {
  it("creates the lead with credentials/CSRF handled by the shared client, then navigates to /leads", async () => {
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(createLead).mockResolvedValue({
      id: "l1",
      company_name: "Acme Co",
      website: null,
      industry: null,
      contact_name: null,
      contact_email: null,
      source: null,
      notes: null,
      status: "new",
      created_at: "now",
      updated_at: "now",
    });

    render(<NewLeadPage />);
    fillRequiredField();
    fireEvent.click(screen.getByRole("button", { name: /create lead/i }));

    await waitFor(() => expect(createLead).toHaveBeenCalled());
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/leads"));
  });

  it("on a 401, redirects via the unauthorized handler instead of showing a form error", async () => {
    const redirectOnUnauthorized = vi.fn().mockReturnValue(true);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(redirectOnUnauthorized);
    vi.mocked(createLead).mockRejectedValue(new ApiError(401, "Not authenticated"));

    render(<NewLeadPage />);
    fillRequiredField();
    fireEvent.click(screen.getByRole("button", { name: /create lead/i }));

    await waitFor(() => expect(redirectOnUnauthorized).toHaveBeenCalled());
    expect(pushMock).not.toHaveBeenCalled();
    expect(screen.queryByText("Not authenticated")).toBeNull();
  });

  it("on a non-auth failure, re-throws so the shared LeadForm shows its own error message", async () => {
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(createLead).mockRejectedValue(new ApiError(409, "Conflicting request."));

    render(<NewLeadPage />);
    fillRequiredField();
    fireEvent.click(screen.getByRole("button", { name: /create lead/i }));

    await waitFor(() => expect(screen.getByText("Conflicting request.")).not.toBeNull());
    expect(pushMock).not.toHaveBeenCalled();
  });
});
