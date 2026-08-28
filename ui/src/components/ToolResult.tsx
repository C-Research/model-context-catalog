interface Props {
  status: number;
  body: string;
}

export function ToolResult({ status, body }: Props) {
  const ok = status >= 200 && status < 300;
  return (
    <div className={`tool-result ${ok ? "tool-result--ok" : "tool-result--error"}`}>
      <div className="tool-result__status">Status: {status}</div>
      <pre className="tool-result__body">{body}</pre>
    </div>
  );
}
