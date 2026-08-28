import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  ApiError,
  clearStoredApiKey,
  getStoredApiKey,
  setStoredApiKey,
  whoami as fetchWhoAmI,
} from "../api";
import type { WhoAmI } from "../api";

interface AuthContextValue {
  apiKey: string | null;
  identity: WhoAmI | null;
  loading: boolean;
  error: string | null;
  setApiKey: (key: string) => Promise<void>;
  clearApiKey: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState<string | null>(null);
  const [identity, setIdentity] = useState<WhoAmI | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Resolves a key against GET /whoami. Stores it optimistically first, since
  // api.ts reads the key straight from localStorage — a 401 rolls that back
  // rather than persisting a known-bad key.
  const resolve = useCallback(async (key: string) => {
    setLoading(true);
    setError(null);
    setStoredApiKey(key);
    setApiKeyState(key);
    try {
      const info = await fetchWhoAmI();
      setIdentity(info);
    } catch (err) {
      clearStoredApiKey();
      setApiKeyState(null);
      setIdentity(null);
      setError(
        err instanceof ApiError && err.status === 401
          ? "Invalid or expired API key."
          : "Could not verify API key.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const stored = getStoredApiKey();
    if (stored) {
      void resolve(stored);
    }
  }, [resolve]);

  const clearApiKey = useCallback(() => {
    clearStoredApiKey();
    setApiKeyState(null);
    setIdentity(null);
    setError(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ apiKey, identity, loading, error, setApiKey: resolve, clearApiKey }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
