// Best-effort scalar coercion for free-typed list/dict values: JSON literals
// (numbers, booleans, null, quoted strings) parse to their real type; plain
// text that isn't valid JSON is kept as-is, since that's what a user typing
// `admin` or a bare URL almost always means.
export function coerceScalar(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
