const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Must match backend/app/config.py's defaults exactly -- these are names,
// not secrets, so hardcoding them here is fine (the actual token VALUES
// live only in cookies the browser manages).
//
// csrf_token / csrf_preauth are deliberately NOT HttpOnly on the backend
// (see backend/app/api/v1/auth.py) specifically so this file can read them
// and echo them back as the X-CSRF-Token header -- that's the whole
// "double-submit" design. session_id, by contrast, IS HttpOnly: this file
// never reads it and never could -- document.cookie simply does not expose
// it. The browser still sends it automatically on every request below
// because of `credentials: "include"`.
const CSRF_HEADER_NAME = "X-CSRF-Token";
const SESSION_CSRF_COOKIE_NAME = "csrf_token";
const PREAUTH_CSRF_COOKIE_NAME = "csrf_preauth";

export type LeadStatus =
  | "new"
  | "researching"
  | "researched"
  | "pitch_ready"
  | "archived";

export const LEAD_STATUSES: LeadStatus[] = [
  "new",
  "researching",
  "researched",
  "pitch_ready",
  "archived",
];

export interface Lead {
  id: string;
  company_name: string;
  website: string | null;
  industry: string | null;
  contact_name: string | null;
  contact_email: string | null;
  source: string | null;
  notes: string | null;
  status: LeadStatus;
  created_at: string;
  updated_at: string;
}

export interface LeadList {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
}

export interface LeadFormInput {
  company_name: string;
  website: string;
  industry: string;
  contact_name: string;
  contact_email: string;
  source: string;
  notes: string;
}

/** Mirrors backend/app/schemas/user.py's UserRead -- never includes the
 * password or any session/CSRF token. */
export interface User {
  id: string;
  email: string;
  is_active: boolean;
  email_verified_at: string | null;
  created_at: string;
}

interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** Raised for both 422 validation errors (fieldErrors populated) and plain
 * string-detail errors (404/409/503/...), so callers can handle either. */
export class ApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return (await response.json()) as T;
  }

  let detail: unknown;
  try {
    detail = (await response.json()).detail;
  } catch {
    throw new ApiError(response.status, `Request failed with status ${response.status}`);
  }

  if (typeof detail === "string") {
    throw new ApiError(response.status, detail);
  }

  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    const messages: string[] = [];
    for (const item of detail as ValidationErrorItem[]) {
      const field = item.loc[item.loc.length - 1];
      if (typeof field === "string") {
        fieldErrors[field] = item.msg;
      }
      messages.push(item.msg);
    }
    throw new ApiError(response.status, messages.join("; "), fieldErrors);
  }

  throw new ApiError(response.status, `Request failed with status ${response.status}`);
}

/** Reads one of the two intentionally-JavaScript-readable CSRF cookies.
 * Never call this with "session_id" -- that cookie is HttpOnly and will
 * never show up in document.cookie no matter what; this function only
 * exists for the two cookies the backend deliberately left readable. */
function readCsrfCookie(name: typeof SESSION_CSRF_COOKIE_NAME | typeof PREAUTH_CSRF_COOKIE_NAME): string | null {
  if (typeof document === "undefined") return null; // server-side render, no cookies yet
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/** Shared fetch wrapper for every backend call in this file.
 *
 * - `credentials: "include"` is what makes the browser attach the
 *   HttpOnly session_id cookie on the request, and allow a Set-Cookie
 *   response to actually be stored -- required on every call, since the
 *   frontend (port 3000) and backend (port 8000) are different origins.
 * - `csrfCookieName`, when given, reads that cookie's current value and
 *   sends it back as the X-CSRF-Token header the backend's double-submit
 *   check compares against. Omit it for GET requests and for the two
 *   endpoints (csrf-token, and anything before a session exists) that
 *   don't need it.
 */
async function apiFetch(
  path: string,
  init: RequestInit = {},
  csrfCookieName?: typeof SESSION_CSRF_COOKIE_NAME | typeof PREAUTH_CSRF_COOKIE_NAME
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (csrfCookieName) {
    const token = readCsrfCookie(csrfCookieName);
    if (token) headers.set(CSRF_HEADER_NAME, token);
  }
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
}

async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  csrfCookieName?: typeof SESSION_CSRF_COOKIE_NAME | typeof PREAUTH_CSRF_COOKIE_NAME
): Promise<T> {
  const response = await apiFetch(path, init, csrfCookieName);
  return handleResponse<T>(response);
}

function toPayload(input: LeadFormInput): Record<string, unknown> {
  // Blank optional fields are sent as null (clears the field on PATCH,
  // ignored on create) rather than empty strings, which would fail the
  // backend's HttpUrl/EmailStr validation.
  return {
    company_name: input.company_name.trim(),
    website: input.website.trim() || null,
    industry: input.industry.trim() || null,
    contact_name: input.contact_name.trim() || null,
    contact_email: input.contact_email.trim() || null,
    source: input.source.trim() || null,
    notes: input.notes.trim() || null,
  };
}

export async function listLeads(params: {
  page: number;
  pageSize: number;
  status?: LeadStatus | "";
  signal?: AbortSignal;
}): Promise<LeadList> {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);

  // GET, so no CSRF header needed -- but credentials are still required:
  // this is the authenticated user's own leads, scoped server-side by
  // their session, not by anything the client sends in the query string.
  return apiRequest<LeadList>(`/api/v1/leads?${query}`, { signal: params.signal });
}

export async function getLead(id: string, signal?: AbortSignal): Promise<Lead> {
  return apiRequest<Lead>(`/api/v1/leads/${id}`, { signal });
}

export async function createLead(input: LeadFormInput): Promise<Lead> {
  return apiRequest<Lead>(
    "/api/v1/leads",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toPayload(input)),
    },
    SESSION_CSRF_COOKIE_NAME
  );
}

export async function updateLead(
  id: string,
  input: LeadFormInput,
  status: LeadStatus
): Promise<Lead> {
  return apiRequest<Lead>(
    `/api/v1/leads/${id}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...toPayload(input), status }),
    },
    SESSION_CSRF_COOKIE_NAME
  );
}

export async function archiveLead(id: string): Promise<Lead> {
  return apiRequest<Lead>(`/api/v1/leads/${id}`, { method: "DELETE" }, SESSION_CSRF_COOKIE_NAME);
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

/** Ensures the browser holds a valid pre-authentication CSRF cookie,
 * fetching one if it's missing or invalid. The backend endpoint itself is
 * idempotent (won't reissue an already-valid cookie -- see
 * backend/app/api/v1/auth.py), so calling this defensively before every
 * register()/login() call is cheap and removes any ordering requirement
 * on the caller (e.g. a form that re-renders without remounting). */
export async function fetchCsrfToken(): Promise<void> {
  const response = await apiFetch("/api/v1/auth/csrf-token", { method: "GET" });
  if (!response.ok) {
    throw new ApiError(response.status, "Could not prepare the form for submission. Please retry.");
  }
}

export async function register(email: string, password: string): Promise<User> {
  await fetchCsrfToken();
  return apiRequest<User>(
    "/api/v1/auth/register",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    },
    PREAUTH_CSRF_COOKIE_NAME
  );
}

export async function login(email: string, password: string): Promise<User> {
  await fetchCsrfToken();
  return apiRequest<User>(
    "/api/v1/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    },
    PREAUTH_CSRF_COOKIE_NAME
  );
}

/** Resolves to the logged-in user, or throws ApiError(401) if there is no
 * valid session. Callers (the auth context built in Stage C) are
 * expected to treat a 401 here as "unauthenticated", not as an
 * unexpected failure. */
export async function me(): Promise<User> {
  return apiRequest<User>("/api/v1/auth/me");
}

export async function logout(): Promise<void> {
  await apiRequest<{ status: string }>("/api/v1/auth/logout", { method: "POST" }, SESSION_CSRF_COOKIE_NAME);
}
