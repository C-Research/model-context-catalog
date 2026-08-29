import type { ReactNode } from "react";

// Seven glyphs cover every icon this app uses. Inlining them as plain SVG
// avoids shipping an entire icon-font family (~600KB across woff2/ttf) plus
// its CSS for a handful of glyphs — see the FontAwesome removal this
// replaced. Add a new case here only when a new icon is actually needed.
export type IconName =
  | "book-open"
  | "search"
  | "arrow-left"
  | "arrow-right"
  | "key"
  | "sign-out"
  | "sun"
  | "moon"
  | "copy"
  | "check";

const PATHS: Record<IconName, ReactNode> = {
  "book-open": (
    <path d="M12 5.5C10.3 4.4 8 4 5.5 4H4v14h1.5c2.5 0 4.8.4 6.5 1.5 1.7-1.1 4-1.5 6.5-1.5H20V4h-1.5c-2.5 0-4.8.4-6.5 1.5Zm0 0v14" />
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M20 20l-4.8-4.8" />
    </>
  ),
  "arrow-left": <path d="M19 12H5m6-7-7 7 7 7" />,
  "arrow-right": <path d="M5 12h14m-6-7 7 7-7 7" />,
  key: (
    <>
      <circle cx="7.5" cy="15.5" r="3.5" />
      <path d="M10.6 12.6 20 3.2M17 6.2l2 2M14 9.2l2 2" />
    </>
  ),
  "sign-out": (
    <>
      <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" />
      <path d="M15 8l4 4-4 4M19 12H9" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
    </>
  ),
  moon: <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" />,
  copy: (
    <>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </>
  ),
  check: <path d="M4 12l5 5L20 6" />,
};

interface Props {
  name: IconName;
  className?: string;
}

export function Icon({ name, className }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1em"
      height="1em"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className ? `icon ${className}` : "icon"}
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
