/* ─── Enums ──────────────────────────────────────────────── */
export type IndexStatus = "idle" | "pending" | "running" | "done" | "error";
export type HealthGrade = "A" | "B" | "C" | "D" | "F";

/* ─── Developer / Repo ───────────────────────────────────── */
export interface DeveloperResponse {
  id: string;
  github_username: string;
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  ai_persona: string | null;
  skill_scores: Record<string, number> | null;
  index_status: IndexStatus;
  indexed_at: string | null;
  created_at: string;
  peak_commit_day: string | null;
  commit_frequency_per_week: number | null;
  total_commits: number | null;
  total_repos: number | null;
}

export interface RepoResponse {
  id: string;
  github_id: number;
  name: string;
  description: string | null;
  primary_language: string | null;
  all_languages: Record<string, number> | null;
  stars: number;
  forks: number;
  last_commit_at: string | null;
  health_score: number;
  health_grade: HealthGrade;
  has_readme: boolean;
  has_tests: boolean;
  has_ci: boolean;
  has_docker: boolean;
  has_license: boolean;
  commit_count: number;
  open_issues: number;
  closed_issues: number;
}

export interface ProfileStatsResponse {
  total_repos: number;
  total_stars: number;
  total_forks: number;
  total_commits: number;
  primary_language: string | null;
  language_percentages: Record<string, number>;
  avg_health_score: number;
  repos_with_tests: number;
  repos_with_ci: number;
}

export interface ProfileResponse {
  developer: DeveloperResponse;
  repos: RepoResponse[];
  stats: ProfileStatsResponse;
}

/* ─── Analyze ────────────────────────────────────────────── */
export interface AnalyzeRequest {
  github_username: string;
}

export interface AnalyzeResponse {
  developer_id: string;
  job_id: string;
  status: IndexStatus;
  message: string;
}

/* ─── WebSocket progress ─────────────────────────────────── */
export interface WsProgressMessage {
  type: "started" | "progress" | "done" | "error";
  repos_done: number;
  repos_total: number;
  repo?: string;
  message?: string;
}

/* ─── AI streaming ───────────────────────────────────────── */
export type ComponentType =
  | "commit_heatmap"
  | "skill_radar"
  | "growth_timeline"
  | "code_pattern"
  | "repo_comparison"
  | "developer_persona"
  | "hire_recommendation"
  | "text";

export interface StreamComponent {
  type: ComponentType;
  text?: string;
  data?: unknown;
}
