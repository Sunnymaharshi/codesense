/**
 * Add these functions + types to src/lib/api.ts
 */

// ─── Compare ────────────────────────────────────────────────
export async function compareProfiles(
  user1: string,
  user2: string,
): Promise<{ left: ProfileResponse; right: ProfileResponse }> {
  return request(`/api/compare/${encodeURIComponent(user1)}/${encodeURIComponent(user2)}`);
}

// ─── Snapshots ──────────────────────────────────────────────
export interface SnapshotResponse {
  id: string;
  taken_at: string;
  total_repos: number;
  avg_health_score: number;
  total_stars: number;
}

export async function takeSnapshot(username: string): Promise<SnapshotResponse> {
  return request(`/api/snapshot/${encodeURIComponent(username)}`, { method: "POST" });
}

export async function listSnapshots(username: string): Promise<{ snapshots: SnapshotResponse[] }> {
  return request(`/api/snapshots/${encodeURIComponent(username)}`);
}

// ─── Re-index (force) ───────────────────────────────────────
export async function reindexUser(username: string): Promise<AnalyzeResponse> {
  return request(`/api/analyze?force=true`, {
    method: "POST",
    body: JSON.stringify({ github_username: username }),
  });
}
