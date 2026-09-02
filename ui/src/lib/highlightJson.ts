// Regex-based JSON syntax highlighting — no dependency, because the only
// thing that ever needs highlighting here is JSON.stringify's own output
// (tool results), not arbitrary source in arbitrary languages. A real
// highlighter (Prism, highlight.js, Shiki) would be solving a much bigger
// problem than this app has.
//
// Safe against injection: the whole string is HTML-escaped *first*, so a
// tool result containing "<script>" becomes literal text before the regex
// ever wraps a token in a <span> — nothing from a result value can break
// out of the markup it's placed in.
const HTML_ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };

function escapeHtml(text: string): string {
  return text.replace(/[&<>]/g, (char) => HTML_ESCAPES[char]);
}

const JSON_TOKEN =
  /"(?:\\u[a-fA-F0-9]{4}|\\.|[^\\"])*"(\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;

export function highlightJson(json: string): string {
  return escapeHtml(json).replace(JSON_TOKEN, (match) => {
    if (match.startsWith('"')) {
      return `<span class="${match.endsWith(":") ? "json-key" : "json-string"}">${match}</span>`;
    }
    if (match === "true" || match === "false") {
      return `<span class="json-boolean">${match}</span>`;
    }
    if (match === "null") {
      return `<span class="json-null">${match}</span>`;
    }
    return `<span class="json-number">${match}</span>`;
  });
}
