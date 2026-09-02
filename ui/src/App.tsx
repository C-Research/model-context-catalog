import { useEffect, useState } from "react";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { Icon } from "./components/Icon";
import { IdentityBadge } from "./components/IdentityBadge";
import { ThemeToggle } from "./components/ThemeToggle";
import { ToolSearch } from "./components/ToolSearch";
import { ToolDetail } from "./components/ToolDetail";

// mcc/routes.py's /ui route has no SPA fallback for unmatched sub-paths — it
// serves *only* /ui and its static assets, 404ing on anything else. So the
// selected tool lives in a query param (?tool=), never a path segment: a
// query string doesn't change what the server matches on a fresh load or
// refresh, but it's still enough for pushState/popstate to make Back/
// Forward and deep-linking to a specific tool work.
function toolFromLocation(): string | null {
  return new URLSearchParams(window.location.search).get("tool");
}

function pushToolState(key: string | null) {
  const url = new URL(window.location.href);
  if (key) {
    url.searchParams.set("tool", key);
  } else {
    url.searchParams.delete("tool");
  }
  window.history.pushState(null, "", url);
}

// One entry point, one mounted route (/ui) — no router library. This
// component itself owns the only navigation state the app has: which tool,
// if any, is selected, and a group carried over from a detail-page tag click.
export default function App() {
  const [selectedKey, setSelectedKey] = useState<string | null>(() => toolFromLocation());
  const [initialGroup, setInitialGroup] = useState<string | null>(null);

  // The only two things that change the URL are handleSelect/goToList below
  // (both via pushState) — this just keeps React in sync when the browser's
  // own Back/Forward buttons move through the history they created.
  useEffect(() => {
    function handlePopState() {
      setSelectedKey(toolFromLocation());
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function handleSelect(key: string) {
    setInitialGroup(null);
    setSelectedKey(key);
    pushToolState(key);
  }

  // Shared by the plain "Back to catalog" button and a group tag clicked on
  // the detail page — both land on the list, the latter also seeding a
  // filter. Always pushState rather than history.back(): a tool page can be
  // reached directly (a shared link, a refresh), where back() would leave
  // the app entirely instead of returning to the list.
  function goToList(group: string | null) {
    setInitialGroup(group);
    setSelectedKey(null);
    pushToolState(null);
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <div className="app">
          {/* md-header: styled directly by orange.css, not app.css. Its
              inner content shares .app__main's width/centering, via the
              same selector, so the header lines up with the page body
              instead of drifting to its own margins. */}
          <header className="app__header md-header">
            <div className="app__header-inner app__main">
              <div className="app__heading">
                <h1 className="app__title">
                  <Icon name="book-open" className="app__title-icon" /> Model Context Catalog
                </h1>
                <p className="app__eyebrow">search &rarr; inspect &rarr; execute</p>
              </div>
              <div className="app__header-actions">
                <IdentityBadge />
                <ThemeToggle />
              </div>
            </div>
          </header>
          <main className="app__main md-typeset">
            {selectedKey ? (
              <ToolDetail
                toolKey={selectedKey}
                onBack={() => goToList(null)}
                onFilterGroup={goToList}
              />
            ) : (
              <ToolSearch onSelect={handleSelect} initialGroup={initialGroup} />
            )}
          </main>
        </div>
      </AuthProvider>
    </ThemeProvider>
  );
}
