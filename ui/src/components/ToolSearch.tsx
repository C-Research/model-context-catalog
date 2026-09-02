import { useEffect, useRef, useState } from "react";
import { listTools, searchTools } from "../api";
import type { SearchResult, Tool } from "../api";
import { useAuth } from "../context/AuthContext";
import { GroupFilter } from "./GroupFilter";
import { Icon } from "./Icon";
import { ToolList } from "./ToolList";

interface Props {
  onSelect: (key: string) => void;
  // Seeds the group filter on mount — set when arriving here from a group
  // tag clicked on the detail page, rather than from the filter row itself.
  initialGroup?: string | null;
}

const DEBOUNCE_MS = 250;
const PAGE_SIZE = 10;
// Matches mcc/routes.py's _MAX_PAGE_LIMIT — the largest single request the
// server allows. Used only for the group-harvesting scan below, so that
// scan takes as few round trips as the server permits (one, for any catalog
// up to 50 tools) instead of walking it PAGE_SIZE-at-a-time.
const MAX_PAGE_LIMIT = 50;

// /tools has no "list distinct groups" endpoint, so populating the filter
// row's option set means walking every page — following has_more/next_offset
// exactly like any other client, rather than asking for it all in one
// oversized request the server would reject. Deliberately unfiltered by
// group, since this is the source of the filter's own options.
async function scanAllGroups(): Promise<string[]> {
  const groups = new Set<string>();
  let offset = 0;
  for (;;) {
    const page = await listTools({ offset, limit: MAX_PAGE_LIMIT });
    for (const tool of page.items) {
      for (const group of tool.groups) groups.add(group);
    }
    if (!page.hasMore || page.nextOffset === null) break;
    offset = page.nextOffset;
  }
  return [...groups].sort();
}

export function ToolSearch({ onSelect, initialGroup }: Props) {
  const { apiKey } = useAuth();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<(Tool | SearchResult)[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(() =>
    initialGroup ? new Set([initialGroup]) : new Set(),
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const listTopRef = useRef<HTMLDivElement>(null);
  // Guards the very first run of the identity effect below, so it doesn't
  // immediately wipe out the initialGroup seed above — it should only clear
  // the filter on a *later* apiKey change, not the mount that set it up.
  const hasRunIdentityEffect = useRef(false);

  // The full accessible tool list drives the group filter's options,
  // independent of any active search query — otherwise the option set would
  // shrink to whatever the current search matched, which is confusing.
  const [availableGroups, setAvailableGroups] = useState<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    if (hasRunIdentityEffect.current) {
      // A stale selection could otherwise reference a group sign-in/out just
      // made unavailable, silently filtering everything out with no visible
      // chip left to undo it. Offset resets here too — a page position from
      // the previous identity's result set has no meaning under a new one.
      setSelectedGroups(new Set());
      setOffset(0);
    } else {
      // First run — don't clobber a seeded initialGroup.
      hasRunIdentityEffect.current = true;
    }
    scanAllGroups()
      .then((groups) => {
        if (!cancelled) setAvailableGroups(groups);
      })
      .catch(() => {
        /* leave availableGroups empty — the filter row just won't render */
      });
    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  // Re-fetch on sign-in/sign-out, offset, or group-filter changes too, not
  // just query — /tools and /search now filter and paginate server-side
  // (mcc/routes.py's ?groups=&offset=&limit=), so every one of these is a
  // real request, not a local re-slice.
  useEffect(() => {
    let cancelled = false;
    const trimmed = query.trim();
    const groups = [...selectedGroups];
    setLoading(true);
    setError(null);

    const timer = setTimeout(
      () => {
        const fetcher = trimmed
          ? searchTools(trimmed, { offset, limit: PAGE_SIZE, groups })
          : listTools({ offset, limit: PAGE_SIZE, groups });
        fetcher
          .then((page) => {
            if (cancelled) return;
            setItems(page.items);
            setHasMore(page.hasMore);
            setNextOffset(page.nextOffset);
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
  }, [query, apiKey, offset, selectedGroups]);

  // Clicking Next from the bottom control (the common case for a full page)
  // would otherwise leave the viewport scrolled to where the old page's
  // list ended — jump back to the list's top anchor so the new page starts
  // in view.
  function goToPage(nextOffset: number) {
    setOffset(Math.max(0, nextOffset));
    listTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function toggleGroup(group: string) {
    setOffset(0);
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

  const currentPage = offset / PAGE_SIZE;

  // Same control rendered above and below the list — with 10 per page a
  // long results list means the "next page" nav at the bottom is often a
  // full scroll away, so it's duplicated at the top rather than moved.
  // No "of N" total — the API only ever tells us has_more, never a count.
  const pagination = (offset > 0 || hasMore) && (
    <div className="tool-search__pagination">
      <button type="button" disabled={offset === 0} onClick={() => goToPage(offset - PAGE_SIZE)}>
        <Icon name="arrow-left" /> Prev
      </button>
      <span className="tool-search__page-count">page {currentPage + 1}</span>
      <button
        type="button"
        disabled={!hasMore || nextOffset === null}
        onClick={() => nextOffset !== null && goToPage(nextOffset)}
      >
        Next <Icon name="arrow-right" />
      </button>
    </div>
  );

  return (
    <div className="tool-search">
      <span className="tool-search__input-wrap">
        <Icon name="search" />
        <input
          type="search"
          placeholder="Search the tool catalog…"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOffset(0);
          }}
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
          <div ref={listTopRef} />
          {pagination}
          <ToolList
            tools={items}
            onSelect={onSelect}
            selectedGroups={selectedGroups}
            onToggleGroup={toggleGroup}
          />
          {pagination}
        </>
      )}
    </div>
  );
}
