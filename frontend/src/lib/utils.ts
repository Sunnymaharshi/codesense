import type { HealthGrade } from "./types";

/* ─── Language colour map ────────────────────────────────── */
const LANG_COLORS: Record<string, string> = {
  TypeScript: "#3178c6",
  JavaScript: "#f7df1e",
  Python: "#3572a5",
  Rust: "#dea584",
  Go: "#00add8",
  Java: "#b07219",
  "C++": "#f34b7d",
  C: "#555555",
  "C#": "#178600",
  Ruby: "#701516",
  PHP: "#4f5d95",
  Swift: "#f05138",
  Kotlin: "#a97bff",
  Dart: "#00b4ab",
  Scala: "#c22d40",
  Elixir: "#6e4a7e",
  Haskell: "#5e5086",
  CSS: "#563d7c",
  HTML: "#e34c26",
  Shell: "#89e051",
  Dockerfile: "#384d54",
  Vue: "#41b883",
  Svelte: "#ff3e00",
};

export function getLangColor(language: string | null): string {
  if (!language) return "var(--color-lang-default)";
  return LANG_COLORS[language] ?? "var(--color-lang-default)";
}

/* ─── Health grade helpers ───────────────────────────────── */
export function getGradeColor(grade: HealthGrade): string {
  switch (grade) {
    case "A": return "var(--color-grade-a)";
    case "B": return "var(--color-grade-b)";
    case "C": return "var(--color-grade-c)";
    case "D":
    case "F": return "var(--color-grade-d)";
  }
}

export function getGradeBg(grade: HealthGrade): string {
  switch (grade) {
    case "A": return "var(--color-grade-a-bg)";
    case "B": return "var(--color-grade-b-bg)";
    case "C": return "var(--color-grade-c-bg)";
    case "D":
    case "F": return "var(--color-grade-d-bg)";
  }
}

/* ─── Number formatting ──────────────────────────────────── */
export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

export function formatPercent(n: number): string {
  return `${Math.round(n)}%`;
}

/* ─── Date helpers ───────────────────────────────────────── */
export function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

/* ─── clsx-like ──────────────────────────────────────────── */
export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}
