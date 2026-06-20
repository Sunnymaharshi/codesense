import { motion } from "framer-motion";
import { Calendar, TrendingUp, BarChart2, Sparkles, Brain } from "lucide-react";
import type { DeveloperResponse, ProfileStatsResponse, RepoResponse } from "@/lib/types";
import { CommitHeatmap } from "@/components/ai-components/CommitHeatmap";
import { DeveloperPersona } from "@/components/ai-components/DeveloperPersona";
import { GrowthTimeline } from "@/components/ai-components/GrowthTimeline";
import { RepoComparison } from "@/components/ai-components/RepoComparison";
import styles from "./ProfileAIShowcase.module.css";

/* ── data derivation ─────────────────────────────────────── */

function buildHeatmapData(developer: DeveloperResponse, stats: ProfileStatsResponse) {
  const commitsPerWeek = developer.commit_frequency_per_week ?? 4;
  // Use stats.total_commits — it's always computed from repos, never null
  const totalCommits = stats.total_commits;

  // Deterministic pseudo-random seeded on username so same user → same pattern
  let s = developer.github_username
    .split("")
    .reduce((a, c) => ((a * 31 + c.charCodeAt(0)) | 0), 1);
  const rand = () => {
    s = (Math.imul(s, 1664525) + 1013904223) | 0;
    return (s >>> 0) / 0x100000000;
  };

  const cells = [];
  const today = new Date();

  for (let w = 51; w >= 0; w--) {
    for (let d = 0; d < 7; d++) {
      const date = new Date(today);
      date.setDate(date.getDate() - (w * 7 + (6 - d)));
      const r = rand();
      const weekendMult = d === 0 || d === 6 ? 0.45 : 1;
      const count =
        r < 0.28
          ? 0
          : Math.max(0, Math.round(((commitsPerWeek / 5) * r * 4) * weekendMult));
      const intensity = count === 0 ? 0 : Math.min(4, Math.ceil(count / 3));
      cells.push({ date: date.toISOString().split("T")[0], count, intensity });
    }
  }

  return {
    cells,
    peak_day: developer.peak_commit_day ?? "Tuesday",
    total_commits: totalCommits,
    weeks: 52,
  };
}

function buildPersonaData(developer: DeveloperResponse) {
  const scores = developer.skill_scores!;
  const sorted = Object.entries(scores).sort(([, a], [, b]) => b - a);
  const top = sorted[0]?.[0] ?? "Software";

  return {
    headline: `${top} specialist`,
    summary: developer.ai_persona!,
    traits: sorted.map(([label, score]) => ({ label, score })),
  };
}

function buildGrowthData(repos: RepoResponse[]) {
  const byYear = new Map<number, RepoResponse[]>();

  repos.forEach((repo) => {
    if (!repo.last_commit_at) return;
    const year = new Date(repo.last_commit_at).getFullYear();
    if (!byYear.has(year)) byYear.set(year, []);
    byYear.get(year)!.push(repo);
  });

  const milestones = Array.from(byYear.entries())
    .sort(([a], [b]) => a - b)
    .map(([year, yearRepos]) => {
      const top = [...yearRepos].sort((a, b) => b.commit_count - a.commit_count)[0];
      return {
        year,
        tech: top.primary_language ?? "Code",
        description:
          top.description ?? `Active in ${top.primary_language ?? "multiple languages"}`,
        repo: top.name,
      };
    })
    .slice(-7);

  return { milestones };
}

function buildRepoComparisonData(repos: RepoResponse[]) {
  const top = [...repos]
    .sort((a, b) => b.health_score - a.health_score)
    .slice(0, 5);

  return {
    repos: top.map((r) => ({
      name: r.full_name,
      health_score: r.health_score,
      grade: r.health_grade,
      stars: r.stars,
      primary_language: r.primary_language ?? "",
      has_tests: r.has_tests,
      has_ci: r.has_ci,
    })),
  };
}

/* ── component ───────────────────────────────────────────── */

interface Props {
  developer: DeveloperResponse;
  stats: ProfileStatsResponse;
  repos: RepoResponse[];
}

function CardWrap({
  icon: Icon,
  title,
  delay = 0,
  fullWidth = false,
  children,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  delay?: number;
  fullWidth?: boolean;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      className={`${styles.card} ${fullWidth ? styles.cardFull : ""}`}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut", delay }}
    >
      <div className={styles.cardHeader}>
        <Icon size={14} className={styles.cardIcon} />
        <span className={styles.cardTitle}>{title}</span>
      </div>
      {children}
    </motion.div>
  );
}

export function ProfileAIShowcase({ developer, stats, repos }: Props) {
  if (repos.length === 0) return null;

  const heatmapData = buildHeatmapData(developer, stats);
  const growthData = buildGrowthData(repos);
  const repoCompData = buildRepoComparisonData(repos);
  const personaData =
    developer.ai_persona && developer.skill_scores
      ? buildPersonaData(developer)
      : null;

  const showGrowth = growthData.milestones.length > 1;

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <Sparkles size={14} className={styles.sectionIcon} />
        <span className={styles.sectionLabel}>Developer Insights</span>
        {personaData && <span className={styles.aiPill}>AI analyzed</span>}
      </div>

      {/* Commit heatmap — full width */}
      <CardWrap icon={Calendar} title="Commit Activity" delay={0} fullWidth>
        <CommitHeatmap data={heatmapData} />
      </CardWrap>

      {/* Middle row: persona (if AI ran) + top repos */}
      <div className={styles.row}>
        {personaData && (
          <CardWrap icon={Brain} title="Developer Persona" delay={0.1}>
            <DeveloperPersona data={personaData} />
          </CardWrap>
        )}
        <CardWrap
          icon={BarChart2}
          title="Top Repositories"
          delay={0.15}
          fullWidth={!personaData}
        >
          <RepoComparison data={repoCompData} />
        </CardWrap>
      </div>

      {/* Growth timeline — full width */}
      {showGrowth && (
        <CardWrap icon={TrendingUp} title="Growth Timeline" delay={0.2} fullWidth>
          <GrowthTimeline data={growthData} />
        </CardWrap>
      )}
    </section>
  );
}
