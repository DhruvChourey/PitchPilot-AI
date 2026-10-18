"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import AuthForm from "@/components/AuthForm";
import Reveal from "@/components/Reveal";

export default function RegisterPage() {
  const { status, register } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/leads");
    }
  }, [status, router]);

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="mx-auto flex w-full max-w-sm flex-col gap-4 px-4 py-10 sm:px-6">
        <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-6 text-sm text-text-muted">
          <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
          {status === "authenticated" ? "Redirecting..." : "Checking your session..."}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-start justify-center px-4 py-10 sm:px-6">
      <Reveal className="w-full max-w-sm rounded-2xl border border-border bg-surface p-6 shadow-2xl shadow-black/30 sm:p-8">
        <div className="mb-6 flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-text">Create Account</h1>
          <p className="text-sm text-text-muted">Start tracking leads with PitchPilot AI.</p>
        </div>

        <AuthForm mode="register" onSubmit={register} />

        <p className="mt-6 text-center text-sm text-text-faint">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-accent-hover underline underline-offset-4">
            Log in
          </Link>
        </p>
      </Reveal>
    </div>
  );
}
