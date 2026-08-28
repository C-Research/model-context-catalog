import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

// Material's own scheme names — "default" = light, "slate" = dark. Reusing
// them (rather than inventing "light"/"dark") is what lets orange.css's
// [data-md-color-scheme="..."] selectors apply unmodified.
export type ColorScheme = "default" | "slate";

const STORAGE_KEY = "mcc_color_scheme";

function initialScheme(): ColorScheme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "default" || stored === "slate") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "slate" : "default";
}

interface ThemeContextValue {
  scheme: ColorScheme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [scheme, setScheme] = useState<ColorScheme>(initialScheme);

  useEffect(() => {
    document.documentElement.dataset.mdColorScheme = scheme;
    localStorage.setItem(STORAGE_KEY, scheme);
  }, [scheme]);

  const toggle = useCallback(() => {
    setScheme((prev) => (prev === "default" ? "slate" : "default"));
  }, []);

  return <ThemeContext.Provider value={{ scheme, toggle }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}
