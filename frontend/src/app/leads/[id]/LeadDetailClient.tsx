"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ApiError,
  archiveLead,
  getLead,
  updateLead,
  type Lead,
  type LeadFormInput,
  type LeadStatus,
  LEAD_STATUSES,
} from "@/lib/api";
import { useRedirectOnUnauthorized } from "@/lib/auth";
import LeadForm from "@/components/LeadForm";
import StatusBadge from "@/components/StatusBadge";
import Reveal from "@/components/Reveal";

type LoadState = "loading" | "loaded" | "error" | "not_found";

function toFormInput(lead: Lead): LeadFormInput {
  return {
    company_name: lead.company_name,
    website: lead.website ?? "",
    industry: lead.industry ?? "",
    contact_name: lead.contact_name ?? "",
    contact_email: lead.contact_email ?? "",
    source: lead.source ?? "",
    notes: lead.notes ?? "",
  };
}

export default function LeadDetailClient({ id: leadId }: { id: string }) {
  const router = useRouter();

  const [lead, setLead] = useState<Lead | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [status, setStatus] = useState<LeadStatus>("new");
  const [statusSaving, setStatusSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const redirectOnUnauthorized = useRedirectOnUnauthorized();

  useEffect(() => {
    const controller = new AbortController();
    getLead(leadId, controller.signal)
      .then((data) => {
        setLead(data);
        setStatus(data.status);
        setState("loaded");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (redirectOnUnauthorized(err)) return; // session expired mid-visit -- off to /login, not an error screen
        if (err instanceof ApiError && err.status === 404) {
          setState("not_found");
          return;
        }
        setErrorMessage(err instanceof ApiError ? err.message : "Failed to load lead.");
        setState("error");
      });
    return () => controller.abort();
  }, [leadId, redirectOnUnauthorized]);

  async function handleSubmit(input: LeadFormInput) {
    try {
      const updated = await updateLead(leadId, input, status);
      setLead(updated);
      setFeedback("Changes saved.");
    } catch (err) {
      if (redirectOnUnauthorized(err)) return;
      throw err; // let LeadForm's own catch show field/validation errors as usual
    }
  }

  async function handleStatusChange(newStatus: LeadStatus) {
    if (!lead) return;
    setStatus(newStatus);
    setStatusSaving(true);
    setFeedback(null);
    try {
      const updated = await updateLead(leadId, toFormInput(lead), newStatus);
      setLead(updated);
      setFeedback("Status updated.");
    } catch (err) {
      setStatus(lead.status); // revert on failure, don't leave UI out of sync
      if (redirectOnUnauthorized(err)) return;
      setErrorMessage(
        err instanceof ApiError ? err.message : "Failed to update status."
      );
    } finally {
      setStatusSaving(false);
    }
  }

  async function handleArchive() {
    if (!lead) return;
    const confirmed = window.confirm(
      `Archive ${lead.company_name}? This won't permanently delete it, but it will be marked as archived.`
    );
    if (!confirmed) return;

    setArchiving(true);
    try {
      await archiveLead(leadId);
      router.push("/leads");
    } catch (err) {
      if (redirectOnUnauthorized(err)) return;
      setErrorMessage(err instanceof ApiError ? err.message : "Failed to archive lead.");
      setArchiving(false);
    }
  }

  if (state === "loading") {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4 px-4 py-10 sm:px-6">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-6 text-sm text-text-muted">
          <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
          Loading lead...
        </div>
      </div>
    );
  }

  if (state === "not_found") {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4 px-4 py-10 sm:px-6">
        <Link href="/leads" className="text-sm text-text-faint transition-colors hover:text-text-muted">
          &larr; Back to leads
        </Link>
        <div className="rounded-xl border border-border bg-surface px-4 py-6 text-center text-sm text-text-muted">
          Lead not found.
        </div>
      </div>
    );
  }

  if (state === "error" || !lead) {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4 px-4 py-10 sm:px-6">
        <Link href="/leads" className="text-sm text-text-faint transition-colors hover:text-text-muted">
          &larr; Back to leads
        </Link>
        <div className="rounded-xl border border-danger/30 bg-danger-soft/40 px-4 py-3 text-sm text-red-300">
          {errorMessage}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-start justify-center px-4 py-10 sm:px-6">
      <Reveal className="w-full max-w-xl rounded-2xl border border-border bg-surface p-6 shadow-2xl shadow-black/30 sm:p-8">
        <div className="mb-6 flex flex-col gap-1">
          <Link href="/leads" className="w-fit text-sm text-text-faint transition-colors hover:text-text-muted">
            &larr; Back to leads
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-text">{lead.company_name}</h1>
            <StatusBadge status={lead.status} />
          </div>
        </div>

        <div className="mb-5 flex items-center gap-3">
          <label htmlFor="status" className="text-sm font-medium text-text-muted">
            Status
          </label>
          <select
            id="status"
            value={status}
            disabled={statusSaving}
            onChange={(e) => handleStatusChange(e.target.value as LeadStatus)}
            className="rounded-lg border border-border-strong bg-surface-2 px-3 py-1.5 text-sm text-text outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/25 disabled:opacity-50"
          >
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          {statusSaving && <span className="text-xs text-text-faint">Saving...</span>}
        </div>

        {feedback && (
          <div className="mb-5 rounded-lg border border-success/30 bg-success-soft/40 px-3 py-2 text-sm text-emerald-300">
            {feedback}
          </div>
        )}

        {errorMessage && (
          <div className="mb-5 rounded-lg border border-danger/30 bg-danger-soft/40 px-3 py-2 text-sm text-red-300">
            {errorMessage}
          </div>
        )}

        <LeadForm initialValues={toFormInput(lead)} submitLabel="Save Changes" onSubmit={handleSubmit} />

        <div className="mt-6 border-t border-border pt-5">
          <button
            type="button"
            onClick={handleArchive}
            disabled={archiving || lead.status === "archived"}
            className="rounded-lg border border-danger/40 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-danger-soft/40 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {lead.status === "archived"
              ? "Already archived"
              : archiving
                ? "Archiving..."
                : "Archive Lead"}
          </button>
        </div>
      </Reveal>
    </div>
  );
}
