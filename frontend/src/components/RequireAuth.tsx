"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";

/** Wraps pages that require a logged-in session (see app/leads/layout.tsx).
 *
 * The three states matter in a specific order:
 * - "loading": still waiting on the one real /me check -- show a loading
 *   row, never the page's real content and never a redirect yet (we don't
 *   know the answer yet, so guessing either way would be wrong).
 * - "unauthenticated": redirect to /login, and render nothing in the
 *   meantime -- this is what stops protected content from flashing on
 *   screen before the redirect takes effect.
 * - "authenticated": render the real page.
 */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4 px-4 py-10 sm:px-6">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-6 text-sm text-text-muted">
          <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
          Checking your session...
        </div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}
