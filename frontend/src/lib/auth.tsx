"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { ApiError, login as apiLogin, logout as apiLogout, me, register as apiRegister, type User } from "./api";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Flips local state to unauthenticated without calling the backend --
   * for when a request elsewhere (e.g. a lead fetch) already got a 401
   * back, so we already know the session is gone. See
   * useRedirectOnUnauthorized below, which is the function pages
   * actually call. */
  handleUnauthorized: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Wraps the whole app (see app/layout.tsx). On mount, the *only* source
 * of truth for "is anyone logged in" is a real call to the backend's
 * `GET /api/v1/auth/me` -- never a locally-stored boolean, never
 * localStorage/sessionStorage. A 401 from that call means
 * "unauthenticated", not an error to retry or alarm about. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    me()
      .then((resolvedUser) => {
        if (!mountedRef.current) return;
        setUser(resolvedUser);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!mountedRef.current) return;
        setUser(null);
        setStatus("unauthenticated");
      });
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const loggedInUser = await apiLogin(email, password);
    setUser(loggedInUser);
    setStatus("authenticated");
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    // Registering only creates the account -- the backend doesn't start a
    // session for it (no cookies are set by POST /auth/register). Log in
    // immediately after with the same credentials so "create an account"
    // feels like one step to the person using the form, not two.
    await apiRegister(email, password);
    try {
      const loggedInUser = await apiLogin(email, password);
      setUser(loggedInUser);
      setStatus("authenticated");
    } catch {
      // Registration itself succeeded -- only the automatic follow-up
      // login failed (e.g. a rate limit tripped in the same moment).
      // Don't claim to be logged in; let the caller send the person to
      // the login page instead, with a message explaining why.
      setStatus("unauthenticated");
      throw new Error("Your account was created, but we couldn't log you in automatically. Please log in.");
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      // Clear local state even if the network call itself failed (e.g.
      // the session was already gone) -- the user's intent was to leave
      // the authenticated state, and we should always honor that locally.
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const handleUnauthorized = useCallback(() => {
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, login, register, logout, handleUnauthorized }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

/** For any page that calls an authenticated backend endpoint directly
 * (the lead list/detail/mutation calls -- RequireAuth only covers the
 * *initial* page load, not a session that expires while already on the
 * page). Call the returned function in a catch block with whatever was
 * thrown; it returns true (and already redirected to /login) if that was
 * a 401, so the caller can skip setting its own generic error message. */
export function useRedirectOnUnauthorized() {
  const { handleUnauthorized } = useAuth();
  const router = useRouter();

  return useCallback(
    (err: unknown): boolean => {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        router.replace("/login");
        return true;
      }
      return false;
    },
    [handleUnauthorized, router]
  );
}
