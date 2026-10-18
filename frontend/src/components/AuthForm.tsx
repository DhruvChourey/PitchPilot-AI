"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api";

interface AuthFormProps {
  mode: "login" | "register";
  onSubmit: (email: string, password: string) => Promise<void>;
}

export default function AuthForm({ mode, onSubmit }: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return; // prevent duplicate submissions while in flight

    setSubmitting(true);
    setFormError(null);
    setFieldErrors({});

    try {
      await onSubmit(email.trim(), password);
      // On success the caller (the page) redirects away; no local reset
      // needed before that happens.
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors);
        if (Object.keys(err.fieldErrors).length === 0) {
          setFormError(err.message);
        }
      } else {
        setFormError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-border-strong bg-surface-2 px-3 py-2.5 text-sm text-text outline-none transition-colors placeholder:text-text-faint focus:border-accent focus:ring-2 focus:ring-accent/25";
  const errorInputClass = "border-danger/60 focus:border-danger focus:ring-danger/25";

  const submitLabel = mode === "login" ? "Log In" : "Create Account";
  const submittingLabel = mode === "login" ? "Logging in..." : "Creating account...";

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="email" className="text-sm font-medium text-text-muted">
          Email<span className="text-danger"> *</span>
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={`${inputClass} ${fieldErrors.email ? errorInputClass : ""}`}
        />
        {fieldErrors.email && <p className="text-xs text-red-400">{fieldErrors.email}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="password" className="text-sm font-medium text-text-muted">
          Password<span className="text-danger"> *</span>
        </label>
        <input
          id="password"
          type="password"
          required
          minLength={mode === "register" ? 8 : undefined}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={`${inputClass} ${fieldErrors.password ? errorInputClass : ""}`}
        />
        {mode === "register" && !fieldErrors.password && (
          <p className="text-xs text-text-faint">At least 8 characters.</p>
        )}
        {fieldErrors.password && <p className="text-xs text-red-400">{fieldErrors.password}</p>}
      </div>

      {formError && (
        <div className="rounded-lg border border-danger/30 bg-danger-soft/40 px-3 py-2 text-sm text-red-300">
          {formError}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="accent-gradient rounded-lg px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-950/30 transition-all duration-200 hover:shadow-indigo-900/40 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
      >
        {submitting ? submittingLabel : submitLabel}
      </button>
    </form>
  );
}
