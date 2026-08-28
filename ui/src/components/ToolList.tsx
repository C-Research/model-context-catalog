import type { SearchResult, Tool } from "../api";

interface Props {
  tools: (Tool | SearchResult)[];
  onSelect: (key: string) => void;
}

function isSearchResult(tool: Tool | SearchResult): tool is SearchResult {
  return "score" in tool;
}

export function ToolList({ tools, onSelect }: Props) {
  if (tools.length === 0) {
    return <p className="tool-list__empty">No tools found.</p>;
  }

  return (
    <ul className="tool-list">
      {tools.map((tool) => (
        <li key={tool.key} className="tool-list__item">
          <button
            type="button"
            className="tool-list__button"
            onClick={() => onSelect(tool.key)}
          >
            <span className="tool-list__row">
              <span className="tool-list__key">{tool.key}</span>
              {isSearchResult(tool) && (
                <span className="tool-list__score">{tool.score.toFixed(2)}</span>
              )}
            </span>
            <span className="tool-list__row">
              {tool.groups.map((group) => (
                <span key={group} className="badge">
                  {group}
                </span>
              ))}
            </span>
            <p className="tool-list__description">{tool.description}</p>
          </button>
        </li>
      ))}
    </ul>
  );
}
