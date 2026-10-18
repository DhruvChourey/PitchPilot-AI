"use client";

import { useState } from "react";
import { ApiError, type LeadFormInput } from "@/lib/api";

const EMPTY: LeadFormInput = {
  company_name: "",
  website: "",
  industry: "",
  contact_name: "",
  contact_email: "",
  source: "",
  notes: "",
};

interface LeadFormProps {
  initialValues?: LeadFormInput;
  submitLabel: string;
  onSubmit: (input: LeadFormInput) => Promise<void>;
}

const FIELD_LABELS: Record<keyof LeadFormInput, string> = {
  company_name: "Company name",
  website: "Website",
  industry: "Industry",
  contact_name: "Contact name",
  contact_email: "Contact email",
  source: "Source",
  notes: "Notes",
};

export default function LeadForm({ initialValues, submitLabel, onSubmit }: LeadFormProps) {
  const [values, setValues] = useState<LeadFormInput>(initialValues ?? EMPTY);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof LeadFormInput>(key: K, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return; // prevent duplicate submissions while in flight

    setSubmitting(true);
    setFormError(null);
    setFieldErrors({});

    try {
      await onSubmit(values);
      // On success the caller navigates away; no need to reset local state
      // (component will unmount).
    } catch (err) {
      // Failure: keep the user's input exactly as typed, surface the error.
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors);
        if (Object.keys(err.fieldErrors).length === 0) {
          setFormError(err.message);
        }
      } else {
        setFormError(err instanceof Error ? err.message : "Something went wrong.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-border-strong bg-surface-2 px-3 py-2.5 text-sm text-text outline-none transition-colors placeholder:text-text-faint focus:border-accent focus:ring-2 focus:ring-accent/25";
  const errorInputClass = "border-danger/60 focus:border-danger focus:ring-danger/25";

  function renderField(
    key: keyof LeadFormInput,
    opts: { type?: string; required?: boolean; multiline?: boolean } = {}
  ) {
    const error = fieldErrors[key];
    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={key} className="text-sm font-medium text-text-muted">
          {FIELD_LABELS[key]}
          {opts.required && <span className="text-danger"> *</span>}
        </label>
        {opts.multiline ? (
          <textarea
            id={key}
            rows={3}
            value={values[key]}
            onChange={(e) => update(key, e.target.value)}
            className={`${inputClass} ${error ? errorInputClass : ""} resize-none`}
          />
        ) : (
          <input
            id={key}
            type={opts.type ?? "text"}
            required={opts.required}
            value={values[key]}
            onChange={(e) => update(key, e.target.value)}
            className={`${inputClass} ${error ? errorInputClass : ""}`}
          />
        )}
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      {renderField("company_name", { required: true })}
      {renderField("website", { type: "url" })}
      {renderField("industry")}
      {renderField("contact_name")}
      {renderField("contact_email", { type: "email" })}
      {renderField("source")}
      {renderField("notes", { multiline: true })}

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
        {submitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
