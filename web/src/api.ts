import type { Job, Profile, RunEvent } from "./types";

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(
  /\/$/,
  "",
);
const SESSION_KEY = "helix.session.v1";
export type Session = {
  token: string;
  demo: boolean;
  demo_source?: "public" | "synthetic" | null;
  workspace_id: string;
  profiles: Profile[];
};
export function loadSession(): Session | null {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
  } catch {
    return null;
  }
}
export function saveSession(session: Session) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}
export async function request<T>(
  path: string,
  token?: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(API_BASE + path, { ...options, headers });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "The backend could not be reached." }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : "Please check your input and try again.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export async function followJob<T>(
  id: string,
  token: string,
  onEvents: (events: RunEvent[]) => void,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE}/api/jobs/${id}/events`, {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });
  if (!response.ok || !response.body)
    throw new Error("Could not open the investigation stream.");
  const reader = response.body.getReader(),
    decoder = new TextDecoder();
  let buffer = "";
  const events: RunEvent[] = [];
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let index: number;
      while ((index = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, index);
        buffer = buffer.slice(index + 2);
        const data = frame
          .split("\n")
          .find((line) => line.startsWith("data: "));
        if (data) {
          events.push(JSON.parse(data.slice(6)));
          onEvents([...events]);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
  const job = await request<Job<T>>(`/api/jobs/${id}`, token, { signal });
  if (job.status === "failed")
    throw new Error(job.error || "The investigation could not complete.");
  if (!job.result)
    throw new Error("The run ended before a result was available.");
  return job.result;
}
