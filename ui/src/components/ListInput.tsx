import { useState } from "react";
import type { KeyboardEvent } from "react";
import { coerceScalar } from "../lib/coerce";

interface Props {
  value: unknown[];
  onChange: (next: unknown[]) => void;
  placeholder?: string;
}

function chipLabel(item: unknown): string {
  return typeof item === "string" ? item : JSON.stringify(item);
}

// A plain array of typed values, entered one at a time — the common case for
// a `list` param (list[str] tags, URLs, ids). There's no bounded option set
// on the backend to select from (see api.ts's ToolParam — item type isn't
// preserved), so this is a free-form tag input, not a picker.
export function ListInput({ value, onChange, placeholder }: Props) {
  const [draft, setDraft] = useState("");

  function commit() {
    const text = draft.trim();
    if (!text) return;
    onChange([...value, coerceScalar(text)]);
    setDraft("");
  }

  function removeAt(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      event.preventDefault();
      removeAt(value.length - 1);
    }
  }

  return (
    <div className="list-input">
      {value.map((item, index) => (
        <span key={index} className="list-input__chip">
          {chipLabel(item)}
          <button
            type="button"
            className="list-input__chip-remove"
            aria-label={`Remove ${chipLabel(item)}`}
            onClick={() => removeAt(index)}
          >
            &times;
          </button>
        </span>
      ))}
      <input
        type="text"
        className="list-input__input"
        value={draft}
        placeholder={value.length === 0 ? placeholder : undefined}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commit}
      />
    </div>
  );
}
