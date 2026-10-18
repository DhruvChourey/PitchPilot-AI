import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import LeadsPage from "./page";
import { listLeads, ApiError, type Lead } from "@/lib/api";
import { useRedirectOnUnauthorized } from "@/lib/auth";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, listLeads: vi.fn() };
});

vi.mock("@/lib/auth", () => ({
  useRedirectOnUnauthorized: vi.fn(),
}));

function sampleLead(overrides: Partial<Lead> = {}): Lead {
  return {
    id: "l1",
    company_name: "Acme Co",
    website: null,
    industry: "Manufacturing",
    contact_name: null,
    contact_email: null,
    source: null,
    notes: null,
    status: "new",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("LeadsPage", () => {
  it("renders the fetched leads once loading finishes", async () => {
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(listLeads).mockResolvedValue({ items: [sampleLead()], total: 1, page: 1, page_size: 20 });

    render(<LeadsPage />);

    await waitFor(() => expect(screen.getByText("Acme Co")).not.toBeNull());
    expect(screen.queryByText(/loading leads/i)).toBeNull();
  });

  it("shows the empty state when there are no leads", async () => {
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(listLeads).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });

    render(<LeadsPage />);

    await waitFor(() => expect(screen.getByText(/no leads yet/i)).not.toBeNull());
  });

  it("shows a generic error banner on a non-auth failure", async () => {
    const redirectOnUnauthorized = vi.fn().mockReturnValue(false);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(redirectOnUnauthorized);
    vi.mocked(listLeads).mockRejectedValue(new ApiError(503, "Database unavailable."));

    render(<LeadsPage />);

    await waitFor(() => expect(screen.getByText("Database unavailable.")).not.toBeNull());
    expect(redirectOnUnauthorized).toHaveBeenCalled();
  });

  it("on a 401, defers to the unauthorized redirect and shows no error banner", async () => {
    const redirectOnUnauthorized = vi.fn().mockReturnValue(true);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(redirectOnUnauthorized);
    vi.mocked(listLeads).mockRejectedValue(new ApiError(401, "Not authenticated"));

    render(<LeadsPage />);

    await waitFor(() => expect(redirectOnUnauthorized).toHaveBeenCalled());
    expect(screen.queryByText(/couldn.?t load leads/i)).toBeNull();
    expect(screen.queryByText("Not authenticated")).toBeNull();
  });
});
