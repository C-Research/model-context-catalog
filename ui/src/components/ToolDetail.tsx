import { useEffect, useState } from "react";
import { getTool } from "../api";
import type { CallOutcome, Tool } from "../api";
import { Icon } from "./Icon";
import { ToolCallForm } from "./ToolCallForm";
import { ToolResult } from "./ToolResult";

interface Props {
  toolKey: string;
  onBack: () => void;
}

export function ToolDetail({ toolKey, onBack }: Props) {
  const [tool, setTool] = useState<Tool | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CallOutcome | null>(null);

  useEffect(() => {
    setTool(null);
    setError(null);
    setResult(null);
    getTool(toolKey)
      .then(setTool)
      // 404 is intentionally the same for "unknown" and "not accessible" —
      // render both identically, don't try to distinguish them.
      .catch(() => setError("Tool not found or not accessible."));
  }, [toolKey]);

  return (
    <div className="tool-detail">
      <button type="button" className="tool-detail__back" onClick={onBack}>
        <Icon name="arrow-left" /> Back to catalog
      </button>

      {error && <p className="tool-detail__error">{error}</p>}

      {tool && (
        <>
          <div className="tool-detail__record">
            <h2 className="tool-detail__key">{tool.key}</h2>
            <span className="tool-detail__tags">
              {tool.groups.map((group) => (
                <span key={group} className="tag">
                  {group}
                </span>
              ))}
            </span>
            <p className="tool-detail__description">{tool.description}</p>
          </div>
          {tool.example && <pre className="tool-detail__example">{tool.example}</pre>}

          <ToolCallForm tool={tool} onResult={setResult} />
          {result && <ToolResult status={result.status} body={result.body} />}
        </>
      )}
    </div>
  );
}
