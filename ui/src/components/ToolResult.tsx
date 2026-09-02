import { useEffect, useRef, useState } from "react";
import { highlightJson } from "../lib/highlightJson";
import { Icon } from "./Icon";

interface Props {
  status: number;
  body: string;
}

const COPIED_RESET_MS = 1500;

// routes.py's tool_execute sends different shapes depending on what ran:
// plain text for an ordinary result or an error message/traceback, or
// {"exit_code", "stdout", "stderr"} for an exec-backed tool — always via a
// 200, since running the subprocess and reporting its own exit status *is*
// the request succeeding (see the HTTP-status discussion this replaced).
// That means HTTP status alone can't tell a caller whether the exec ran
// clean, so the exit code — not the transport status — drives this view.
interface ExecResult {
  exit_code: number;
  stdout: string;
  stderr: string;
}

function parseExecResult(body: string): ExecResult | null {
  try {
    const parsed = JSON.parse(body);
    if (
      parsed &&
      typeof parsed === "object" &&
      typeof parsed.exit_code === "number" &&
      typeof parsed.stdout === "string" &&
      typeof parsed.stderr === "string"
    ) {
      return parsed as ExecResult;
    }
  } catch {
    /* not JSON, or not this shape — falls through to the generic view */
  }
  return null;
}

// Pretty-prints when the body parses as JSON, returning null otherwise
// (plain-text errors, tracebacks, and any non-exec result that isn't JSON)
// so the caller knows whether there's anything to syntax-highlight.
//
// routes.py's non-exec success path is str(result), not json.dumps(result)
// — so a plain Python string result loses the quotes that would make it
// valid JSON, and True/False/None are capitalized. Both are recoverable
// without a real Python parser: recognize the three literals directly, and
// treat a bare single-line value as one string. A Python dict/list repr
// ({...}/[...] with single-quoted keys) is left alone — unlike those three
// literals, parsing that properly needs real Python-literal syntax, not a
// regex, the same reasoning as the exec-tuple case this view replaced.
function formatJson(body: string): string | null {
  try {
    return JSON.stringify(JSON.parse(body), null, 2);
  } catch {
    const trimmed = body.trim();
    if (trimmed === "True") return "true";
    if (trimmed === "False") return "false";
    if (trimmed === "None") return "null";
    if (trimmed && !trimmed.includes("\n") && !/^[{[]/.test(trimmed)) {
      return JSON.stringify(trimmed);
    }
    return null;
  }
}

function useCopy(text: string) {
  const [copied, setCopied] = useState(false);
  const resetTimer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(resetTimer.current), []);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.clearTimeout(resetTimer.current);
    resetTimer.current = window.setTimeout(() => setCopied(false), COPIED_RESET_MS);
  }

  return { copied, handleCopy };
}

function CopyButton({ text }: { text: string }) {
  const { copied, handleCopy } = useCopy(text);
  return (
    <button type="button" className="tool-result__copy" onClick={handleCopy} disabled={!text}>
      <Icon name={copied ? "check" : "copy"} /> {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function ToolResult({ status, body }: Props) {
  const exec = parseExecResult(body);

  if (exec) {
    const ok = exec.exit_code === 0;
    return (
      <div className={`tool-result ${ok ? "tool-result--ok" : "tool-result--error"}`}>
        <div className="tool-result__header">
          <span className="tool-result__status">exit code {exec.exit_code}</span>
        </div>
        <div className="tool-result__stream">
          <div className="tool-result__stream-header">
            <span className="tool-result__stream-label">stderr</span>
            <CopyButton text={exec.stderr} />
          </div>
          <pre className="tool-result__body">{exec.stderr || "(empty)"}</pre>
        </div>
        <div className="tool-result__stream">
          <div className="tool-result__stream-header">
            <span className="tool-result__stream-label">stdout</span>
            <CopyButton text={exec.stdout} />
          </div>
          <pre className="tool-result__body">{exec.stdout || "(empty)"}</pre>
        </div>
      </div>
    );
  }

  const httpOk = status >= 200 && status < 300;
  const asJson = formatJson(body);
  return (
    <div className={`tool-result ${httpOk ? "tool-result--ok" : "tool-result--error"}`}>
      <div className="tool-result__header">
        <span className="tool-result__status">Status: {status}</span>
        {/* Always the raw body, not the normalized display form above —
            True/None/an unquoted string are re-shaped only for rendering,
            not into text that actually appeared in the response. */}
        <CopyButton text={body} />
      </div>
      {asJson ? (
        <pre
          className="tool-result__body"
          dangerouslySetInnerHTML={{ __html: highlightJson(asJson) }}
        />
      ) : (
        <pre className="tool-result__body">{body}</pre>
      )}
    </div>
  );
}
