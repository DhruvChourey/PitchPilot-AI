import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import LeadDetailClient from "./LeadDetailClient";
import { archiveLead, getLead, updateLead, ApiError, type Lead } from "@/lib/api";
import { useRedirectOnUnauthorized } from "@/lib/auth";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getLead: vi.fn(), updateLead: vi.fn(), archiveLead: vi.fn() };
});

vi.mock("@/lib/auth", () => ({
  useRedirectOnUnauthorized: vi.fn(),
}));

function sampleLead(overrides: Partial<Lead> = {}): Lead {
  return {
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
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("LeadDetailClient -- load", () => {
  it("renders the lead once loaded", async () => {
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(getLead).mockResolvedValue(sampleLead());

    render(<LeadDetailClient id="l1" />);

    await waitFor(() => expect(screen.getByText("Acme Co")).not.toBeNull());
  });

  it("shows a not-found message on a 404", async () => {
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(getLead).mockRejectedValue(new ApiError(404, "Lead not found"));

    render(<LeadDetailClient id="l1" />);

    await waitFor(() => expect(screen.getByText(/lead not found/i)).not.toBeNull());
  });

  it("on a 401, defers to the unauthorized redirect instead of an error screen", async () => {
    const redirectOnUnauthorized = vi.fn().mockReturnValue(true);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(redirectOnUnauthorized);
    vi.mocked(getLead).mockRejectedValue(new ApiError(401, "Not authenticated"));

    render(<LeadDetailClient id="l1" />);

    await waitFor(() => expect(redirectOnUnauthorized).toHaveBeenCalled());
    expect(screen.queryByText(/not authenticated/i)).toBeNull();
    expect(screen.queryByText(/lead not found/i)).toBeNull();
  });
});

describe("LeadDetailClient -- status change", () => {
  it("updates the lead and shows feedback on success", async () => {
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(getLead).mockResolvedValue(sampleLead());
    vi.mocked(updateLead).mockResolvedValue(sampleLead({ status: "researching" }));

    render(<LeadDetailClient id="l1" />);
    await waitFor(() => expect(screen.getByText("Acme Co")).not.toBeNull());

    fireEvent.change(screen.getByLabelText(/^status$/i), { target: { value: "researching" } });

    await waitFor(() => expect(screen.getByText(/status updated/i)).not.toBeNull());
  });

  it("on a 401, reverts the select and redirects instead of showing an error", async () => {
    // Mock the hook once to always hand back this *same* function
    // instance -- flipping its return value later still affects every
    // closure already holding a reference to it, without needing the
    // component to re-render and re-call the hook.
    const redirectOnUnauthorized = vi.fn().mockReturnValue(false);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(redirectOnUnauthorized);
    vi.mocked(getLead).mockResolvedValue(sampleLead());
    render(<LeadDetailClient id="l1" />);
    await waitFor(() => expect(screen.getByText("Acme Co")).not.toBeNull());

    redirectOnUnauthorized.mockReturnValue(true);
    vi.mocked(updateLead).mockRejectedValue(new ApiError(401, "Not authenticated"));

    fireEvent.change(screen.getByLabelText(/^status$/i), { target: { value: "researching" } });

    await waitFor(() => expect(redirectOnUnauthorized).toHaveBeenCalled());
    expect(screen.queryByText(/failed to update status/i)).toBeNull();
  });
});

describe("LeadDetailClient -- archive", () => {
  it("archives after confirmation and navigates to /leads", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(getLead).mockResolvedValue(sampleLead());
    vi.mocked(archiveLead).mockResolvedValue(sampleLead({ status: "archived" }));

    render(<LeadDetailClient id="l1" />);
    await waitFor(() => expect(screen.getByText("Acme Co")).not.toBeNull());

    fireEvent.click(screen.getByRole("button", { name: /archive lead/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/leads"));
  });

  it("does not call archiveLead at all if the confirmation is declined", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(vi.fn().mockReturnValue(false));
    vi.mocked(getLead).mockResolvedValue(sampleLead());

    render(<LeadDetailClient id="l1" />);
    await waitFor(() => expect(screen.getByText("Acme Co")).not.toBeNull());

    fireEvent.click(screen.getByRole("button", { name: /archive lead/i }));

    expect(archiveLead).not.toHaveBeenCalled();
  });

  it("on a 401, defers to the unauthorized redirect instead of showing an error", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const redirectOnUnauthorized = vi.fn().mockReturnValue(false);
    vi.mocked(useRedirectOnUnauthorized).mockReturnValue(redirectOnUnauthorized);
    vi.mocked(getLead).mockResolvedValue(sampleLead());
    render(<LeadDetailClient id="l1" />);
    await waitFor(() => expect(screen.getByText("Acme Co")).not.toBeNull());

    redirectOnUnauthorized.mockReturnValue(true);
    vi.mocked(archiveLead).mockRejectedValue(new ApiError(401, "Not authenticated"));

    fireEvent.click(screen.getByRole("button", { name: /archive lead/i }));

    await waitFor(() => expect(redirectOnUnauthorized).toHaveBeenCalled());
    expect(pushMock).not.toHaveBeenCalled();
    expect(screen.queryByText(/failed to archive lead/i)).toBeNull();
  });
});
