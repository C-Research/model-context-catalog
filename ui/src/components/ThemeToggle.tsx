import { useTheme } from "../context/ThemeContext";

export function ThemeToggle() {
  const { scheme, toggle } = useTheme();
  const isDark = scheme === "slate";

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      <i className={`fa-solid ${isDark ? "fa-sun" : "fa-moon"}`} aria-hidden="true" />
    </button>
  );
}
