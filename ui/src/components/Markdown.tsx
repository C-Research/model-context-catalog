import { micromark } from "micromark";

interface Props {
  text: string;
  className?: string;
}

// Descriptions come from the backend as markdown (mcc/templates/
// tool_signature.md drops tool.description/param.description in as bare
// paragraphs, rendered server-side via a bare markdown-it preset for
// /tools?format=html). micromark matches that feature set — plain
// CommonMark, no GFM/table plugins — and, unlike marked, doesn't parse raw
// HTML tags in the source into live elements by default (no
// allowDangerousHtml), so an injected <script>/onerror in a tool's
// description renders as literal escaped text instead of running.
export function Markdown({ text, className }: Props) {
  const html = micromark(text);
  return (
    <div
      className={className ? `markdown ${className}` : "markdown"}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
