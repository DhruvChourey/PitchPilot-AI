"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";
import { ApiError, listLeads, type Lead, type LeadStatus, LEAD_STATUSES } from "@/lib/api";
import { useRedirectOnUnauthorized } from "@/lib/auth";
import StatusBadge from "@/components/StatusBadge";
import Reveal from "@/components/Reveal";

const PAGE_SIZE = 20;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [overallTotal, setOverallTotal] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // useTransition's isPending covers the "loading" state without calling
  // setState synchronously inside the effect (React 19 supports passing an
  // async function to startTransition directly -- "Actions"). The previous
  // list stays visible while a new page/filter loads, which also reads
  // better than a full-page flash on every click.
  const [isPending, startTransition] = useTransition();
  const redirectOnUnauthorized = useRedirectOnUnauthorized();

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    const controller = new AbortController();
    startTransition(async () => {
      try {
        const result = await listLeads({
          page,
          pageSize: PAGE_SIZE,
          status: statusFilter,
          signal: controller.signal,
        });
        setLeads(result.items);
        setTotal(result.total);
        setErrorMessage(null);
        // Keep an accurate, unfiltered total for the summary card -- cheap
        // (page_size=1, only the count matters) and only needed once per
        // filter state, not on every page change.
        if (!statusFilter) {
          setOverallTotal(result.total);
        } else if (overallTotal === null) {
          const unfiltered = await listLeads({
            page: 1,
            pageSize: 1,
            status: "",
            signal: controller.signal,
          });
          setOverallTotal(unfiltered.total);
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        if (redirectOnUnauthorized(err)) return; // session expired mid-visit -- off to /login, not an error banner
        setErrorMessage(err instanceof ApiError ? err.message : "Failed to load leads.");
      }
    });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- overallTotal intentionally excluded: it's a cache, not a trigger.
  }, [page, statusFilter, startTransition, redirectOnUnauthorized]);

  function handleStatusFilterChange(value: string) {
    setStatusFilter(value as LeadStatus | "");
    setPage(1);
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <Reveal stagger className="flex flex-col gap-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-text sm:text-3xl">Leads</h1>
            <p className="mt-1 text-sm text-text-muted">
              Track and manage your prospects, from first contact to pitch-ready.
            </p>
          </div>
          <Link
            href="/leads/new"
            className="accent-gradient inline-flex items-center justify-center gap-1.5 rounded-lg px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-950/30 transition-all duration-200 hover:shadow-indigo-900/40 active:scale-[0.98]"
          >
            <span className="text-base leading-none">+</span> New Lead
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:max-w-sm">
          <StatCard label="Total Leads" value={overallTotal ?? "—"} />
          <StatCard label="Showing" value={total} accent />
        </div>

        <div className="flex items-center gap-3">
          <label htmlFor="status-filter" className="text-sm font-medium text-text-muted">
            Status
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => handleStatusFilterChange(e.target.value)}
            className="rounded-lg border border-border-strong bg-surface-2 px-3 py-1.5 text-sm text-text outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/25"
          >
            <option value="">All</option>
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-3">
          {isPending && (
            <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-6 text-sm text-text-muted">
              <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
              Loading leads...
            </div>
          )}

          {!isPending && errorMessage && (
            <div className="flex flex-col gap-1 rounded-xl border border-danger/30 bg-danger-soft/40 px-4 py-3 text-sm text-red-300">
              <div className="font-medium">Couldn&apos;t load leads</div>
              <p>{errorMessage}</p>
            </div>
          )}

          {!isPending && !errorMessage && leads.length === 0 && (
            <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border-strong px-4 py-14 text-center text-sm text-text-muted">
              <p>No leads yet.</p>
              <Link href="/leads/new" className="font-medium text-accent-hover underline underline-offset-4">
                Create your first lead
              </Link>
            </div>
          )}

          {!isPending && !errorMessage && leads.length > 0 && (
            <Reveal stagger animKey={`${page}-${statusFilter}`} className="flex flex-col gap-2">
              {leads.map((lead) => (
                <Link
                  key={lead.id}
                  href={`/leads/${lead.id}`}
                  className="group flex flex-col gap-2 rounded-xl border border-border bg-surface px-5 py-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-2 hover:shadow-lg hover:shadow-black/20 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex flex-col gap-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text transition-colors group-hover:text-white">
                        {lead.company_name}
                      </span>
                      <StatusBadge status={lead.status} />
                    </div>
                    <div className="flex flex-wrap gap-x-3 text-xs text-text-faint">
                      {lead.industry && <span>{lead.industry}</span>}
                      {lead.contact_name && <span>{lead.contact_name}</span>}
                      {lead.contact_email && <span>{lead.contact_email}</span>}
                    </div>
                  </div>
                  <div className="text-xs text-text-faint">Updated {formatDate(lead.updated_at)}</div>
                </Link>
              ))}
            </Reveal>
          )}

          {!isPending && !errorMessage && totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-2 text-sm">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border border-border-strong px-3 py-1.5 text-text-muted transition-colors hover:bg-surface-2 hover:text-text disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
              >
                Previous
              </button>
              <span className="text-text-faint">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-border-strong px-3 py-1.5 text-text-muted transition-colors hover:bg-surface-2 hover:text-text disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </Reveal>
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: number | string; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-text-faint">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tracking-tight ${accent ? "text-accent-hover" : "text-text"}`}>
        {value}
      </div>
    </div>
  );
}
