"use client";

import { useEffect, useState } from "react";

type Status = "loading" | "connected" | "error";

interface HealthResponse {
  status: string;
  service: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const response = await fetch(`${API_BASE_URL}/health`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Backend responded with status ${response.status}`);
        }

        const data: HealthResponse = await response.json();
        setHealth(data);
        setStatus("connected");
      } catch (err) {
        if (controller.signal.aborted) return;
        setErrorMessage(err instanceof Error ? err.message : "Unknown error");
        setStatus("error");
      }
    }

    checkHealth();

    return () => controller.abort();
  }, []);

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 text-sm text-zinc-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        <span className="h-2 w-2 animate-pulse rounded-full bg-zinc-400" />
        Checking backend connection...
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex flex-col gap-1 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
        <div className="flex items-center gap-2 font-medium">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          Backend unavailable
        </div>
        <p className="text-red-600 dark:text-red-400">
          Could not reach {API_BASE_URL}/health. Make sure the backend is running
          ({errorMessage}).
        </p>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-900 dark:bg-green-950 dark:text-green-300">
      <span className="h-2 w-2 rounded-full bg-green-500" />
      Connected to {health?.service} ({health?.status})
    </div>
  );
}
