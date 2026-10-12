import BackendStatus from "@/components/BackendStatus";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-xl flex-col gap-6 px-6 py-24">
        <div className="flex flex-col gap-2 text-center sm:text-left">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            PitchPilot AI
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            Turn a business lead into evidence-backed research, a tailored sales
            strategy, and a complete pitch deck.
          </p>
        </div>
        <BackendStatus />
      </main>
    </div>
  );
}
