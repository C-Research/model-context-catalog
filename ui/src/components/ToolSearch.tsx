import { useEffect, useMemo, useState } from "react";
import { listTools, searchTools } from "../api";
import type { SearchResult, Tool } from "../api";
import { useAuth } from "../context/AuthContext";
import { GroupFilter } from "./GroupFilter";
import { Icon } from "./Icon";
import { ToolList } from "./ToolList";

interface Props {
  onSelect: (key: string) => void;
}

const DEBOUNCE_MS = 250;
const PAGE_SIZE = 20;

export function ToolSearch({ onSelect }: Props) {
  const { apiKey } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<(Tool | SearchResult)[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  // The full accessible tool list drives the group filter's options,
  // independent of any active search query — otherwise the option set would
  // shrink to whatever the current search matched, which is confusing.
  const [availableGroups, setAvailableGroups] = useState<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    // A stale selection could otherwise reference a group sign-in/out just
    // made unavailable, silently filtering everything out with no visible
    // chip left to undo it.
    setSelectedGroups(new Set());
    listTools()
      .then((tools) => {
        if (cancelled) return;
        const groups = new Set<string>();
        for (const tool of tools) {
          for (const group of tool.groups) groups.add(group);
        }
        setAvailableGroups([...groups].sort());
      })
      .catch(() => {
        /* leave availableGroups empty — the filter row just won't render */
      });
    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  // Re-fetch on sign-in/sign-out too, not just on query changes — the
  // accessible tool set depends on the X-API-Key the caller is using.
  useEffect(() => {
    let cancelled = false;
    const trimmed = query.trim();
    setLoading(true);
    setError(null);
    setPage(0);

    const timer = setTimeout(
      () => {
        const fetcher = trimmed ? searchTools(trimmed) : listTools();
        fetcher
          .then((tools) => {
            if (!cancelled) setResults(tools);
          })
          .catch(() => {
            if (!cancelled) setError("Could not load tools.");
          })
          .finally(() => {
            if (!cancelled) setLoading(false);
          });
      },
      trimmed ? DEBOUNCE_MS : 0,
    );

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, apiKey]);

  function toggleGroup(group: string) {
    setPage(0);
    setSelectedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(group)) {
        next.delete(group);
      } else {
        next.add(group);
      }
      return next;
    });
  }

  const filtered = useMemo(() => {
    if (selectedGroups.size === 0) return results;
    return results.filter((tool) => tool.groups.some((group) => selectedGroups.has(group)));
  }, [results, selectedGroups]);

  // Clamp rather than reset on every filtered-list change — a shrinking list
  // (e.g. toggling a group off elsewhere) should snap back to the last real
  // page instead of always jumping to page 1.
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const paged = filtered.slice(currentPage * PAGE_SIZE, currentPage * PAGE_SIZE + PAGE_SIZE);

  return (
    <div className="tool-search">
      <span className="tool-search__input-wrap">
        <Icon name="search" />
        <input
          type="search"
          placeholder="Search the tool catalog…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="tool-search__input"
        />
      </span>
      {availableGroups.length > 0 && (
        <GroupFilter groups={availableGroups} selected={selectedGroups} onToggle={toggleGroup} />
      )}
      {loading && <p className="tool-search__status">Loading…</p>}
      {error && <p className="tool-search__status tool-search__status--error">{error}</p>}
      {!loading && !error && (
        <>
          <ToolList
            tools={paged}
            onSelect={onSelect}
            selectedGroups={selectedGroups}
            onToggleGroup={toggleGroup}
          />
          {pageCount > 1 && (
            <div className="tool-search__pagination">
              <button
                type="button"
                disabled={currentPage === 0}
                onClick={() => setPage(currentPage - 1)}
              >
                <Icon name="arrow-left" /> Prev
              </button>
              <span className="tool-search__page-count">
                page {currentPage + 1} / {pageCount}
              </span>
              <button
                type="button"
                disabled={currentPage === pageCount - 1}
                onClick={() => setPage(currentPage + 1)}
              >
                Next <Icon name="arrow-right" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
