import { useState } from "react";
import type { FormEvent } from "react";
import { callTool } from "../api";
import type { CallOutcome, Tool, ToolParam } from "../api";

interface Props {
  tool: Tool;
  onResult: (result: CallOutcome) => void;
}

type FieldValue = string | boolean;

function defaultFor(param: ToolParam): FieldValue {
  if (param.type === "bool") return Boolean(param.default);
  if (param.default !== null && param.default !== undefined) return String(param.default);
  return "";
}

// str/int/float/bool map to native inputs; list/dict map to a JSON textarea,
// parsed client-side before submit — there is no richer structured-input
// widget in scope for v1 (see design.md).
export function ToolCallForm({ tool, onResult }: Props) {
  const [values, setValues] = useState<Record<string, FieldValue>>(() => {
    const initial: Record<string, FieldValue> = {};
    for (const param of tool.params) {
      initial[param.name] = defaultFor(param);
    }
    return initial;
  });
  const [jsonErrors, setJsonErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  function updateValue(name: string, value: FieldValue) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  function buildPayload(): Record<string, unknown> | null {
    const payload: Record<string, unknown> = {};
    const errors: Record<string, string> = {};

    for (const param of tool.params) {
      const raw = values[param.name];

      if (param.type === "bool") {
        payload[param.name] = Boolean(raw);
        continue;
      }

      const text = String(raw ?? "").trim();
      if (!text && !param.required) continue;

      if (param.type === "list" || param.type === "dict") {
        try {
          payload[param.name] = text ? JSON.parse(text) : param.type === "list" ? [] : {};
        } catch {
          errors[param.name] = "Invalid JSON.";
        }
        continue;
      }

      if (param.type === "int") {
        payload[param.name] = Number.parseInt(text, 10);
      } else if (param.type === "float") {
        payload[param.name] = Number.parseFloat(text);
      } else {
        payload[param.name] = text;
      }
    }

    setJsonErrors(errors);
    return Object.keys(errors).length === 0 ? payload : null;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const payload = buildPayload();
    if (payload === null) return;

    setSubmitting(true);
    try {
      const outcome = await callTool(tool.key, payload);
      onResult(outcome);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="tool-call-form" onSubmit={handleSubmit}>
      {tool.params.map((param) => (
        <label key={param.name} className="tool-call-form__field">
          <span className="tool-call-form__label">
            {param.name}
            {param.required && <span className="tool-call-form__required">*</span>}
            <span className="tool-call-form__type">{param.type}</span>
          </span>

          {param.type === "bool" ? (
            <input
              type="checkbox"
              checked={Boolean(values[param.name])}
              onChange={(event) => updateValue(param.name, event.target.checked)}
            />
          ) : param.type === "list" || param.type === "dict" ? (
            <textarea
              rows={3}
              placeholder={param.example || (param.type === "list" ? "[]" : "{}")}
              value={String(values[param.name] ?? "")}
              onChange={(event) => updateValue(param.name, event.target.value)}
            />
          ) : (
            <input
              type={param.type === "int" || param.type === "float" ? "number" : "text"}
              required={param.required}
              placeholder={param.example}
              value={String(values[param.name] ?? "")}
              onChange={(event) => updateValue(param.name, event.target.value)}
            />
          )}

          {param.description && (
            <span className="tool-call-form__description">{param.description}</span>
          )}
          {jsonErrors[param.name] && (
            <span className="tool-call-form__error">{jsonErrors[param.name]}</span>
          )}
        </label>
      ))}

      <button type="submit" disabled={submitting}>
        {submitting ? "Running…" : "Call tool"}
      </button>
    </form>
  );
}
