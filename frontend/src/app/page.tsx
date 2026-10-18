import Link from "next/link";
import BackendStatus from "@/components/BackendStatus";
import Reveal from "@/components/Reveal";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-24">
      <Reveal stagger className="flex w-full max-w-xl flex-col gap-6">
        <div className="flex flex-col gap-3 text-center sm:text-left">
          <span className="inline-flex w-fit items-center gap-1.5 self-center rounded-full border border-border-strong bg-surface px-3 py-1 text-xs font-medium text-text-muted sm:self-start">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            AI Sales Intelligence
          </span>
          <h1 className="bg-gradient-to-br from-text via-text to-text-muted bg-clip-text text-4xl font-semibold tracking-tight text-transparent sm:text-5xl">
            PitchPilot AI
          </h1>
          <p className="text-base leading-relaxed text-text-muted">
            Turn a business lead into evidence-backed research, a tailored sales
            strategy, and a complete pitch deck.
          </p>
        </div>
        <BackendStatus />
        <Link
          href="/leads"
          className="group accent-gradient inline-flex items-center justify-center gap-2 rounded-lg px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/40 transition-all duration-200 hover:shadow-indigo-900/50 active:scale-[0.98]"
        >
          View Leads
          <span className="transition-transform duration-200 group-hover:translate-x-0.5">
            &rarr;
          </span>
        </Link>
      </Reveal>
    </div>
  );
}
