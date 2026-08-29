import { useState } from "react";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { Icon } from "./components/Icon";
import { IdentityBadge } from "./components/IdentityBadge";
import { ThemeToggle } from "./components/ThemeToggle";
import { ToolSearch } from "./components/ToolSearch";
import { ToolDetail } from "./components/ToolDetail";

// One entry point, one mounted route (/ui) — no router library. This
// component itself owns the only navigation state the app has: which tool,
// if any, is selected.
export default function App() {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  return (
    <ThemeProvider>
      <AuthProvider>
        <div className="app">
          {/* md-header: styled directly by orange.css, not app.css */}
          <header className="app__header md-header">
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
          </header>
          <main className="app__main md-typeset">
            {selectedKey ? (
              <ToolDetail toolKey={selectedKey} onBack={() => setSelectedKey(null)} />
            ) : (
              <ToolSearch onSelect={setSelectedKey} />
            )}
          </main>
        </div>
      </AuthProvider>
    </ThemeProvider>
  );
}
