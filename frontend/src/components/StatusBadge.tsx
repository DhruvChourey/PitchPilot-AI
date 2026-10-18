import type { LeadStatus } from "@/lib/api";

const STYLES: Record<LeadStatus, string> = {
  new: "bg-indigo-500/10 text-indigo-300 ring-1 ring-inset ring-indigo-500/30",
  researching: "bg-amber-500/10 text-amber-300 ring-1 ring-inset ring-amber-500/30",
  researched: "bg-violet-500/10 text-violet-300 ring-1 ring-inset ring-violet-500/30",
  pitch_ready: "bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/30",
  archived: "bg-white/5 text-text-faint ring-1 ring-inset ring-border-strong",
};

const LABELS: Record<LeadStatus, string> = {
  new: "New",
  researching: "Researching",
  researched: "Researched",
  pitch_ready: "Pitch Ready",
  archived: "Archived",
};

export default function StatusBadge({ status }: { status: LeadStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
