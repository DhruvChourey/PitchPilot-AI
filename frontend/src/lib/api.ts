const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

  const response = await fetch(`${API_BASE_URL}/api/v1/leads?${query}`, {
    signal: params.signal,
  });
  return handleResponse<LeadList>(response);
}

export async function getLead(id: string, signal?: AbortSignal): Promise<Lead> {
  const response = await fetch(`${API_BASE_URL}/api/v1/leads/${id}`, { signal });
  return handleResponse<Lead>(response);
}

export async function createLead(input: LeadFormInput): Promise<Lead> {
  const response = await fetch(`${API_BASE_URL}/api/v1/leads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toPayload(input)),
  });
  return handleResponse<Lead>(response);
}

export async function updateLead(
  id: string,
  input: LeadFormInput,
  status: LeadStatus
): Promise<Lead> {
  const response = await fetch(`${API_BASE_URL}/api/v1/leads/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...toPayload(input), status }),
  });
  return handleResponse<Lead>(response);
}

export async function archiveLead(id: string): Promise<Lead> {
  const response = await fetch(`${API_BASE_URL}/api/v1/leads/${id}`, {
    method: "DELETE",
  });
  return handleResponse<Lead>(response);
}
