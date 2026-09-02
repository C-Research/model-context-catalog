import { useState } from "react";
import type { FormEvent } from "react";
import { callTool } from "../api";
import type { CallOutcome, Tool, ToolParam } from "../api";
import { DictInput } from "./DictInput";
import { ListInput } from "./ListInput";
import { Markdown } from "./Markdown";

interface Props {
  tool: Tool;
  onResult: (result: CallOutcome) => void;
}

type FieldValue = string | boolean | unknown[] | Record<string, unknown>;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function defaultFor(param: ToolParam): FieldValue {
  if (param.type === "bool") return Boolean(param.default);
  if (param.type === "list") return Array.isArray(param.default) ? param.default : [];
  if (param.type === "dict") return isPlainObject(param.default) ? param.default : {};
  if (param.default !== null && param.default !== undefined) return String(param.default);
  return "";
}

function isEmptyStructured(value: FieldValue): boolean {
  return Array.isArray(value) ? value.length === 0 : Object.keys(value as object).length === 0;
}

// str/int/float/bool map to native inputs. list/dict get a structured editor
// (ListInput's tag chips / DictInput's key-value rows) by default, since the
// backend never tells us more than "list" or "dict" — no item type, no
// bounded choices — so a chip/row editor that coerces each value through
// coerceScalar covers the common case (tags, id lists, string maps) without
// guessing at shape. The form-level "advanced" toggle is the escape hatch
// for anything that editor can't represent (nested objects, lists of
// objects) — one switch for every list/dict field, not one per field.
export function ToolCallForm({ tool, onResult }: Props) {
  const [values, setValues] = useState<Record<string, FieldValue>>(() => {
    const initial: Record<string, FieldValue> = {};
    for (const param of tool.params) {
      initial[param.name] = defaultFor(param);
    }
    return initial;
  });
  const [advancedMode, setAdvancedMode] = useState(false);
  const [rawText, setRawText] = useState<Record<string, string>>({});
  const [jsonErrors, setJsonErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const structuredParams = tool.params.filter((p) => p.type === "list" || p.type === "dict");

  function updateValue(name: string, value: FieldValue) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  // Turning advanced mode on seeds every list/dict textarea from its current
  // structured value. Turning it back off discards any unsubmitted raw
  // edits — the structured values in `values` were never touched while
  // advanced, so they reappear exactly as they were before switching.
  function toggleAdvanced() {
    const turningOn = !advancedMode;
    if (turningOn) {
      setRawText((prev) => {
        const next = { ...prev };
        for (const param of structuredParams) {
          next[param.name] = JSON.stringify(values[param.name], null, 2);
        }
        return next;
      });
    }
    setAdvancedMode(turningOn);
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

      if (param.type === "list" || param.type === "dict") {
        if (advancedMode) {
          const text = (rawText[param.name] ?? "").trim();
          if (!text && !param.required) continue;
          try {
            payload[param.name] = text ? JSON.parse(text) : param.type === "list" ? [] : {};
          } catch {
            errors[param.name] = "Invalid JSON.";
          }
          continue;
        }
        if (isEmptyStructured(raw) && !param.required) continue;
        payload[param.name] = raw;
        continue;
      }

      const text = String(raw ?? "").trim();
      if (!text && !param.required) continue;

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
      {structuredParams.length > 0 && (
        <label className="tool-call-form__advanced-toggle">
          <input type="checkbox" checked={advancedMode} onChange={toggleAdvanced} />
          Edit list/dict params as JSON
        </label>
      )}

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
            advancedMode ? (
              <textarea
                rows={3}
                placeholder={param.type === "list" ? "[]" : "{}"}
                value={rawText[param.name] ?? ""}
                onChange={(event) =>
                  setRawText((prev) => ({ ...prev, [param.name]: event.target.value }))
                }
              />
            ) : param.type === "list" ? (
              <ListInput
                value={values[param.name] as unknown[]}
                onChange={(next) => updateValue(param.name, next)}
                placeholder={param.example || "add a value…"}
              />
            ) : (
              <DictInput
                initialValue={values[param.name] as Record<string, unknown>}
                onChange={(next) => updateValue(param.name, next)}
              />
            )
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
            <Markdown text={param.description} className="tool-call-form__description" />
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
