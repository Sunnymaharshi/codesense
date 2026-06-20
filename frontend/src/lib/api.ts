import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ProfileResponse,
} from "./types";

export interface SnapshotResponse {
  id: string;
  taken_at: string;
  total_repos: number;
  avg_health_score: number;
  total_stars: number;
}

const BASE_URL = import.meta.env.VITE_API_URL ?? "";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.detail ?? body?.message ?? message;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<T>;
}

/* ─── Endpoints ──────────────────────────────────────────── */

/** POST /api/analyze — submit a GitHub username for indexing */
export async function analyzeUser(
  username: string,
): Promise<AnalyzeResponse> {
  const body: AnalyzeRequest = { github_username: username };
  return request<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** GET /api/profile/:username — full developer profile */
export async function getProfile(username: string): Promise<ProfileResponse> {
  return request<ProfileResponse>(`/api/profile/${encodeURIComponent(username)}`);
}

/** GET /api/compare/:user1/:user2 — side-by-side profiles */
export async function compareProfiles(
  user1: string,
  user2: string,
): Promise<{ left: ProfileResponse; right: ProfileResponse }> {
  return request(`/api/compare/${encodeURIComponent(user1)}/${encodeURIComponent(user2)}`);
}

/** GET /api/snapshots/:username — list snapshots, newest first */
export async function listSnapshots(
  username: string,
): Promise<{ snapshots: SnapshotResponse[] }> {
  return request(`/api/snapshots/${encodeURIComponent(username)}`);
}

/** POST /api/snapshot/:username — save a snapshot now */
export async function takeSnapshot(username: string): Promise<SnapshotResponse> {
  return request(`/api/snapshot/${encodeURIComponent(username)}`, { method: "POST" });
}

/** POST /api/analyze?force=true — force re-index */
export async function reindexUser(username: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/analyze?force=true", {
    method: "POST",
    body: JSON.stringify({ github_username: username }),
  });
}

export { ApiError };
