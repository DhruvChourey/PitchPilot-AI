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
      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-3 text-sm text-text-muted">
        <span className="h-2 w-2 animate-pulse rounded-full bg-text-faint" />
        Checking backend connection...
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex flex-col gap-1 rounded-lg border border-danger/30 bg-danger-soft/40 px-4 py-3 text-sm text-red-300">
        <div className="flex items-center gap-2 font-medium">
          <span className="h-2 w-2 rounded-full bg-danger" />
          Backend unavailable
        </div>
        <p className="text-red-300/80">
          Could not reach {API_BASE_URL}/health. Make sure the backend is running
          ({errorMessage}).
        </p>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success-soft/40 px-4 py-3 text-sm text-emerald-300">
      <span className="h-2 w-2 rounded-full bg-success" />
      Connected to {health?.service} ({health?.status})
    </div>
  );
}
