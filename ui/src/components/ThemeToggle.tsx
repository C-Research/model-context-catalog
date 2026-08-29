import { useTheme } from "../context/ThemeContext";
import { Icon } from "./Icon";

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
      <Icon name={isDark ? "sun" : "moon"} />
    </button>
  );
}
