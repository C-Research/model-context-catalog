// All calls to the MCC HTTP API live here. Same-origin only — no server URL
// to configure, no CORS. The API key (if any) lives in localStorage and is
// attached as X-API-Key on every request.

const API_KEY_STORAGE_KEY = "mcc_api_key";

export function getStoredApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE_KEY);
}

export function setStoredApiKey(key: string): void {
  localStorage.setItem(API_KEY_STORAGE_KEY, key);
}

export function clearStoredApiKey(): void {
  localStorage.removeItem(API_KEY_STORAGE_KEY);
}

export interface ToolParam {
  name: string;
  type: string;
  required: boolean;
  default: unknown;
  description: string;
  example: string;
}

export interface Tool {
  key: string;
  groups: string[];
  params: ToolParam[];
  return_type: string;
  description: string;
  example: string;
}

export interface SearchResult extends Tool {
  score: number;
}

// Shared shape of /tools and /search's paginated responses.
export interface Page<T> {
  items: T[];
  hasMore: boolean;
  nextOffset: number | null;
}

export interface PageOptions {
  offset?: number;
  limit?: number;
  // Sent as one comma-separated `groups` param — a tool matches if it
  // belongs to any of them (mcc/routes.py's _parse_groups).
  groups?: string[];
}

export interface WhoAmI {
  username: string;
  email: string | null;
  groups: string[];
  tools: string[];
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function requestJson<T>(path: string): Promise<T> {
  const headers = new Headers();
  const key = getStoredApiKey();
  if (key) headers.set("X-API-Key", key);
  const res = await fetch(path, { headers });
  if (!res.ok) {
    throw new ApiError(res.status, (await res.text()) || res.statusText);
  }
  return (await res.json()) as T;
}

function pageParams(params: URLSearchParams, options: PageOptions): URLSearchParams {
  if (options.offset !== undefined) params.set("offset", String(options.offset));
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  if (options.groups && options.groups.length > 0) params.set("groups", options.groups.join(","));
  return params;
}

// /tools?offset=&limit= — {"tools": [...], "has_more": bool, "next_offset": int | null}.
export function listTools(options: PageOptions = {}): Promise<Page<Tool>> {
  const params = pageParams(new URLSearchParams(), options);
  const qs = params.toString();
  return requestJson<{ tools: Tool[]; has_more: boolean; next_offset: number | null }>(
    `/tools${qs ? `?${qs}` : ""}`,
  ).then((res) => ({ items: res.tools, hasMore: res.has_more, nextOffset: res.next_offset }));
}

export function getTool(key: string): Promise<Tool> {
  return requestJson<Tool>(`/tools/${encodeURIComponent(key)}`);
}

export interface SearchToolsOptions extends PageOptions {
  minScore?: number;
}

// /search?q=&min_score=&offset=&limit= — {"results": [...], "has_more": bool, "next_offset": int | null}.
export function searchTools(
  query: string,
  options: SearchToolsOptions = {},
): Promise<Page<SearchResult>> {
  const params = pageParams(new URLSearchParams({ q: query }), options);
  if (options.minScore !== undefined) params.set("min_score", String(options.minScore));
  return requestJson<{ results: SearchResult[]; has_more: boolean; next_offset: number | null }>(
    `/search?${params.toString()}`,
  ).then((res) => ({ items: res.results, hasMore: res.has_more, nextOffset: res.next_offset }));
}

export function whoami(): Promise<WhoAmI> {
  return requestJson<WhoAmI>("/whoami");
}

export interface CallOutcome {
  status: number;
  body: string;
}

// Deliberately does not throw on a non-2xx: POST /tools/{key} always returns
// a plain-text body (success or error) that the UI renders verbatim, per spec.
export async function callTool(
  key: string,
  params: Record<string, unknown>,
): Promise<CallOutcome> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const apiKey = getStoredApiKey();
  if (apiKey) headers.set("X-API-Key", apiKey);
  const res = await fetch(`/tools/${encodeURIComponent(key)}`, {
    method: "POST",
    headers,
    body: JSON.stringify(params),
  });
  const body = await res.text();
  return { status: res.status, body };
}
