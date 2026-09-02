import type { KeyboardEvent } from "react";
import type { SearchResult, Tool } from "../api";
import { Markdown } from "./Markdown";

interface Props {
  tools: (Tool | SearchResult)[];
  onSelect: (key: string) => void;
  selectedGroups: Set<string>;
  onToggleGroup: (group: string) => void;
}

function isSearchResult(tool: Tool | SearchResult): tool is SearchResult {
  return "score" in tool;
}

export function ToolList({ tools, onSelect, selectedGroups, onToggleGroup }: Props) {
  if (tools.length === 0) {
    return (
      <p className="tool-list__empty">
        No tools match — try a different search or clear a group filter.
      </p>
    );
  }

  // A real <button> can't contain the group tags' own <button>s (invalid
  // nesting, and a click on a tag would bubble into the card's own click
  // handler), so the card itself is a div with role="button" — same
  // keyboard operability, but the tags underneath get to be independently
  // clickable filters.
  function handleCardKeyDown(event: KeyboardEvent<HTMLDivElement>, key: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(key);
    }
  }

  return (
    <ul className="tool-list">
      {tools.map((tool) => (
        <li key={tool.key} className="tool-list__item">
          <div
            className="tool-list__button"
            role="button"
            tabIndex={0}
            onClick={() => onSelect(tool.key)}
            onKeyDown={(event) => handleCardKeyDown(event, tool.key)}
          >
            <span className="tool-list__row">
              <span className="tool-list__key">{tool.key}</span>
              {isSearchResult(tool) && (
                <span className="tool-list__score">score {tool.score.toFixed(2)}</span>
              )}
            </span>
            <span className="tool-list__tags">
              {tool.groups.map((group) => (
                <button
                  key={group}
                  type="button"
                  className={`tag${selectedGroups.has(group) ? " tag--active" : ""}`}
                  aria-pressed={selectedGroups.has(group)}
                  onClick={(event) => {
                    event.stopPropagation();
                    onToggleGroup(group);
                  }}
                >
                  {group}
                </button>
              ))}
            </span>
            <Markdown text={tool.description} className="tool-list__description" />
          </div>
        </li>
      ))}
    </ul>
  );
}
