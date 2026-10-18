"use client";

import { useCallback, useSyncExternalStore } from "react";

// A tiny external store per localStorage key, so reading it doesn't need a
// useEffect + setState (which React 19's lint rules flag as a cascading
// render risk) -- useSyncExternalStore is the React-sanctioned way to read
// an external, possibly-SSR-unavailable source like localStorage.
const listeners = new Map<string, Set<() => void>>();

function emit(key: string) {
  listeners.get(key)?.forEach((listener) => listener());
}

export function useLocalStorageBoolean(key: string, defaultValue = false) {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      if (!listeners.has(key)) listeners.set(key, new Set());
      listeners.get(key)!.add(onStoreChange);
      return () => listeners.get(key)?.delete(onStoreChange);
    },
    [key]
  );

  const getSnapshot = useCallback(() => {
    try {
      const raw = window.localStorage.getItem(key);
      return raw === null ? defaultValue : raw === "1";
    } catch {
      return defaultValue; // private browsing / blocked storage
    }
  }, [key, defaultValue]);

  const getServerSnapshot = useCallback(() => defaultValue, [defaultValue]);

  const value = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setValue = useCallback(
    (next: boolean) => {
      try {
        window.localStorage.setItem(key, next ? "1" : "0");
      } catch {
        // Best effort only -- the toggle still works for this tab via emit().
      }
      emit(key);
    },
    [key]
  );

  return [value, setValue] as const;
}
