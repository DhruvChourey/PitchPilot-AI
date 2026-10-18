import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  archiveLead,
  createLead,
  fetchCsrfToken,
  getLead,
  listLeads,
  login,
  logout,
  me,
  register,
  updateLead,
} from "./api";

/** Builds a minimal stand-in for the global `document` object -- just
 * enough `cookie` behavior for api.ts's readCsrfCookie() to work, without
 * pulling in a full jsdom environment (Stage B has no React rendering to
 * test yet). */
function stubDocumentCookie(cookieString: string) {
  vi.stubGlobal("document", { cookie: cookieString });
}

function jsonResponse(status: number, body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("credentials", () => {
  it("includes credentials on a GET lead request", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { items: [], total: 0, page: 1, page_size: 20 }));

    await listLeads({ page: 1, pageSize: 20 });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.credentials).toBe("include");
  });

  it("includes credentials on /auth/me", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, { id: "u1", email: "a@b.com", is_active: true, email_verified_at: null, created_at: "now" })
    );

    await me();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.credentials).toBe("include");
  });

  it("includes credentials on getLead -- regression guard against reverting to the old uncredentialed fetch", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, {
        id: "l1",
        company_name: "Acme",
        website: null,
        industry: null,
        contact_name: null,
        contact_email: null,
        source: null,
        notes: null,
        status: "new",
        created_at: "now",
        updated_at: "now",
      })
    );

    await getLead("l1");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/leads/l1");
    expect(init.credentials).toBe("include");
  });
});

describe("CSRF headers", () => {
  it("fetchCsrfToken() calls the csrf-token endpoint with credentials and no body", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await fetchCsrfToken();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/auth/csrf-token");
    expect(init.method).toBe("GET");
    expect(init.credentials).toBe("include");
  });

  it("register() fetches a pre-auth token first, then echoes it as X-CSRF-Token", async () => {
    stubDocumentCookie("csrf_preauth=the-preauth-value; other=ignored");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(new Response(null, { status: 204 })) // GET /csrf-token
      .mockResolvedValueOnce(
        jsonResponse(201, {
          id: "u1",
          email: "a@b.com",
          is_active: true,
          email_verified_at: null,
          created_at: "now",
        })
      );

    await register("a@b.com", "password123");

    expect(fetchMock).toHaveBeenCalledTimes(2);
    const [registerUrl, registerInit] = fetchMock.mock.calls[1];
    expect(registerUrl).toContain("/api/v1/auth/register");
    const headers = new Headers(registerInit.headers);
    expect(headers.get("X-CSRF-Token")).toBe("the-preauth-value");
    expect(registerInit.credentials).toBe("include");
  });

  it("login() echoes the pre-auth cookie, not the session-bound one", async () => {
    stubDocumentCookie("csrf_preauth=preauth-value; csrf_token=stale-session-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(
        jsonResponse(200, { id: "u1", email: "a@b.com", is_active: true, email_verified_at: null, created_at: "now" })
      );

    await login("a@b.com", "password123");

    const [, loginInit] = fetchMock.mock.calls[1];
    const headers = new Headers(loginInit.headers);
    expect(headers.get("X-CSRF-Token")).toBe("preauth-value");
  });

  it("lead mutations echo the session-bound csrf_token cookie, not the pre-auth one", async () => {
    stubDocumentCookie("csrf_preauth=stale-preauth-value; csrf_token=session-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(201, {
        id: "l1",
        company_name: "Acme",
        website: null,
        industry: null,
        contact_name: null,
        contact_email: null,
        source: null,
        notes: null,
        status: "new",
        created_at: "now",
        updated_at: "now",
      })
    );

    await createLead({
      company_name: "Acme",
      website: "",
      industry: "",
      contact_name: "",
      contact_email: "",
      source: "",
      notes: "",
    });

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(headers.get("X-CSRF-Token")).toBe("session-value");
    expect(init.credentials).toBe("include");
  });

  it("updateLead() echoes the session-bound csrf_token cookie and includes credentials -- regression guard", async () => {
    stubDocumentCookie("csrf_preauth=stale-preauth-value; csrf_token=session-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, {
        id: "l1",
        company_name: "Acme",
        website: null,
        industry: null,
        contact_name: null,
        contact_email: null,
        source: null,
        notes: null,
        status: "researching",
        created_at: "now",
        updated_at: "now",
      })
    );

    await updateLead(
      "l1",
      { company_name: "Acme", website: "", industry: "", contact_name: "", contact_email: "", source: "", notes: "" },
      "researching"
    );

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/leads/l1");
    expect(init.method).toBe("PATCH");
    expect(init.credentials).toBe("include");
    const headers = new Headers(init.headers);
    expect(headers.get("X-CSRF-Token")).toBe("session-value");
  });

  it("archiveLead() echoes the session-bound csrf_token cookie and includes credentials -- regression guard", async () => {
    stubDocumentCookie("csrf_preauth=stale-preauth-value; csrf_token=session-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, {
        id: "l1",
        company_name: "Acme",
        website: null,
        industry: null,
        contact_name: null,
        contact_email: null,
        source: null,
        notes: null,
        status: "archived",
        created_at: "now",
        updated_at: "now",
      })
    );

    await archiveLead("l1");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/leads/l1");
    expect(init.method).toBe("DELETE");
    expect(init.credentials).toBe("include");
    const headers = new Headers(init.headers);
    expect(headers.get("X-CSRF-Token")).toBe("session-value");
  });

  it("logout() sends the session-bound CSRF token", async () => {
    stubDocumentCookie("csrf_token=session-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: "logged out" }));

    await logout();

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(headers.get("X-CSRF-Token")).toBe("session-value");
  });

  it("does not send an X-CSRF-Token header when the relevant cookie is absent", async () => {
    stubDocumentCookie(""); // no cookies at all
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(jsonResponse(403, { detail: "CSRF check failed" }));

    await expect(logout()).rejects.toBeInstanceOf(ApiError);

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(headers.has("X-CSRF-Token")).toBe(false);
  });
});

describe("success responses", () => {
  it("updateLead() parses a successful response into a Lead", async () => {
    stubDocumentCookie("csrf_token=session-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, {
        id: "l1",
        company_name: "Updated Co",
        website: null,
        industry: null,
        contact_name: null,
        contact_email: null,
        source: null,
        notes: null,
        status: "researching",
        created_at: "then",
        updated_at: "now",
      })
    );

    const result = await updateLead(
      "l1",
      { company_name: "Updated Co", website: "", industry: "", contact_name: "", contact_email: "", source: "", notes: "" },
      "researching"
    );

    expect(result.company_name).toBe("Updated Co");
    expect(result.status).toBe("researching");
  });

  it("archiveLead() parses a successful response", async () => {
    stubDocumentCookie("csrf_token=session-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      jsonResponse(200, {
        id: "l1",
        company_name: "Acme",
        website: null,
        industry: null,
        contact_name: null,
        contact_email: null,
        source: null,
        notes: null,
        status: "archived",
        created_at: "then",
        updated_at: "now",
      })
    );

    const result = await archiveLead("l1");

    expect(result.status).toBe("archived");
  });
});

describe("error responses", () => {
  it("me() throws ApiError(401) on no session -- callers treat this as unauthenticated", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(jsonResponse(401, { detail: "Not authenticated" }));

    const error = await me().catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(401);
    expect((error as ApiError).message).toBe("Not authenticated");
  });

  it("login() surfaces a 429 rate-limit error message", async () => {
    stubDocumentCookie("csrf_preauth=preauth-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse(429, { detail: "Too many login attempts, try again later." }));

    const error = await login("a@b.com", "wrong").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(429);
  });

  it("register() surfaces field-level 422 validation errors", async () => {
    stubDocumentCookie("csrf_preauth=preauth-value");
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(
      jsonResponse(422, {
        detail: [{ loc: ["body", "password"], msg: "String should have at least 8 characters", type: "string_too_short" }],
      })
    );

    const error = await register("a@b.com", "short").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).fieldErrors.password).toBe("String should have at least 8 characters");
  });

  it("fetchCsrfToken() throws ApiError without ever touching fieldErrors parsing (204 has no body)", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 503 }));

    await expect(fetchCsrfToken()).rejects.toBeInstanceOf(ApiError);
  });
});
