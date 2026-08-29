import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

interface Props {
  status: number;
  body: string;
}

const COPIED_RESET_MS = 1500;

// The route always sends plain text (str(result) on success, a message or
// traceback on error — see routes.py's tool_execute) — never guaranteed
// JSON either way. Exec-backed tools in particular can return a bare Python
// tuple repr like "(1, '', 'ImportError: ...')" as a normal (200) result,
// which isn't JSON at all. Pretty-print when it parses, fall back to the
// raw string otherwise — never throws, never mangles the tuple case.
function formatBody(body: string): string {
  try {
    return JSON.stringify(JSON.parse(body), null, 2);
  } catch {
    return body;
  }
}

export function ToolResult({ status, body }: Props) {
  const ok = status >= 200 && status < 300;
  const formatted = formatBody(body);
  const [copied, setCopied] = useState(false);
  const resetTimer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(resetTimer.current), []);

  async function handleCopy() {
    await navigator.clipboard.writeText(formatted);
    setCopied(true);
    window.clearTimeout(resetTimer.current);
    resetTimer.current = window.setTimeout(() => setCopied(false), COPIED_RESET_MS);
  }

  return (
    <div className={`tool-result ${ok ? "tool-result--ok" : "tool-result--error"}`}>
      <div className="tool-result__header">
        <span className="tool-result__status">Status: {status}</span>
        <button type="button" className="tool-result__copy" onClick={handleCopy}>
          <Icon name={copied ? "check" : "copy"} /> {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="tool-result__body">{formatted}</pre>
    </div>
  );
}
