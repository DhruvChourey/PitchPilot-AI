"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { createLead, type LeadFormInput } from "@/lib/api";
import LeadForm from "@/components/LeadForm";
import Reveal from "@/components/Reveal";

export default function NewLeadPage() {
  const router = useRouter();

  async function handleSubmit(input: LeadFormInput) {
    await createLead(input);
    router.push("/leads");
  }

  return (
    <div className="flex flex-1 items-start justify-center px-4 py-10 sm:px-6">
      <Reveal className="w-full max-w-xl rounded-2xl border border-border bg-surface p-6 shadow-2xl shadow-black/30 sm:p-8">
        <div className="mb-6 flex flex-col gap-1">
          <Link
            href="/leads"
            className="w-fit text-sm text-text-faint transition-colors hover:text-text-muted"
          >
            &larr; Back to leads
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight text-text">New Lead</h1>
        </div>
        <LeadForm submitLabel="Create Lead" onSubmit={handleSubmit} />
      </Reveal>
    </div>
  );
}
