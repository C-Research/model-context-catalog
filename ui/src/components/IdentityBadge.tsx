import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { Icon } from "./Icon";

export function IdentityBadge() {
  const { apiKey, identity, loading, error, setApiKey, clearApiKey } = useAuth();
  const [input, setInput] = useState("");

  if (apiKey && identity) {
    return (
      <div className="identity-badge">
        <span className="identity-badge__user">{identity.username}</span>
        {identity.groups.length > 0 ? (
          <span className="identity-badge__groups">
            {identity.groups.map((group) => (
              <span key={group} className="tag">
                {group}
              </span>
            ))}
          </span>
        ) : (
          <span className="identity-badge__no-groups">no groups</span>
        )}
        <button type="button" className="identity-badge__signout" onClick={clearApiKey}>
          <Icon name="sign-out" /> Sign out
        </button>
      </div>
    );
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = input.trim();
    if (trimmed) {
      void setApiKey(trimmed);
    }
  }

  return (
    <form className="identity-badge identity-badge--anon" onSubmit={handleSubmit}>
      <span className="identity-badge__anon">Anonymous</span>
      <span className="identity-badge__input-wrap">
        <Icon name="key" />
        <input
          type="password"
          placeholder="API key"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          className="identity-badge__input"
        />
      </span>
      <button type="submit" disabled={loading || !input.trim()}>
        {loading ? "Checking…" : "Connect"}
      </button>
      {error && <span className="identity-badge__error">{error}</span>}
    </form>
  );
}
