import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ProfileResponse,
} from "./types";

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

export { ApiError };
