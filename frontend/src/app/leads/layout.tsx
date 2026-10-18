import RequireAuth from "@/components/RequireAuth";

// Applies to every route under /leads (list, new, detail) -- one guard,
// not one per page, so a future new lead-related page is protected by
// default just by living under this segment.
export default function LeadsLayout({ children }: { children: React.ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}
