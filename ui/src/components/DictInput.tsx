import { useRef, useState } from "react";
import { coerceScalar } from "../lib/coerce";

interface Row {
  id: number;
  key: string;
  value: string;
}

interface Props {
  initialValue: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}

function toDict(rows: Row[]): Record<string, unknown> {
  const dict: Record<string, unknown> = {};
  for (const row of rows) {
    if (!row.key.trim()) continue;
    dict[row.key] = coerceScalar(row.value);
  }
  return dict;
}

// Repeatable key/value rows — the shape a `dict` param actually takes in
// this catalog (e.g. field name -> CSS selector). Uncontrolled: seeded once
// from initialValue, then owns its own row state so an in-progress key
// (empty, or briefly duplicating another) never has to round-trip through a
// real object. Only the derived dict is reported upward, via onChange.
export function DictInput({ initialValue, onChange }: Props) {
  const idRef = useRef(0);
  const [rows, setRows] = useState<Row[]>(() =>
    Object.entries(initialValue).map(([key, val]) => ({
      id: idRef.current++,
      key,
      value: typeof val === "string" ? val : JSON.stringify(val),
    })),
  );

  function update(next: Row[]) {
    setRows(next);
    onChange(toDict(next));
  }

  function updateRow(id: number, field: "key" | "value", text: string) {
    update(rows.map((row) => (row.id === id ? { ...row, [field]: text } : row)));
  }

  function removeRow(id: number) {
    update(rows.filter((row) => row.id !== id));
  }

  function addRow() {
    update([...rows, { id: idRef.current++, key: "", value: "" }]);
  }

  return (
    <div className="dict-input">
      {rows.map((row) => (
        <div key={row.id} className="dict-input__row">
          <input
            type="text"
            className="dict-input__key"
            placeholder="key"
            value={row.key}
            onChange={(event) => updateRow(row.id, "key", event.target.value)}
          />
          <input
            type="text"
            className="dict-input__value"
            placeholder="value"
            value={row.value}
            onChange={(event) => updateRow(row.id, "value", event.target.value)}
          />
          <button
            type="button"
            className="dict-input__remove"
            aria-label="Remove field"
            onClick={() => removeRow(row.id)}
          >
            &times;
          </button>
        </div>
      ))}
      <button type="button" className="dict-input__add" onClick={addRow}>
        + Add field
      </button>
    </div>
  );
}
