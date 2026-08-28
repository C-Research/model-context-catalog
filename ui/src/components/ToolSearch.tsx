import { useEffect, useMemo, useState } from "react";
import { listTools, searchTools } from "../api";
import type { SearchResult, Tool } from "../api";
import { useAuth } from "../context/AuthContext";
import { GroupFilter } from "./GroupFilter";
import { ToolList } from "./ToolList";

interface Props {
  onSelect: (key: string) => void;
}

const DEBOUNCE_MS = 250;

export function ToolSearch({ onSelect }: Props) {
  const { apiKey } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<(Tool | SearchResult)[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="tool-search">
      <span className="tool-search__input-wrap">
        <i className="fa-solid fa-magnifying-glass" aria-hidden="true" />
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
      {!loading && !error && <ToolList tools={filtered} onSelect={onSelect} />}
    </div>
  );
}
