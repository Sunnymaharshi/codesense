import { motion } from "framer-motion";
import { Sparkles, Code2, Activity, ShieldCheck } from "lucide-react";
import type { DeveloperResponse, ProfileStatsResponse } from "@/lib/types";
import { SkillRadar } from "@/components/ai-components/SkillRadar";
import { getLangColor, formatNumber } from "@/lib/utils";
import styles from "./AIInsightCards.module.css";

interface Props {
  developer: DeveloperResponse;
  stats: ProfileStatsResponse;
}

/* Word-by-word reveal for persona text */
function RevealText({ text }: { text: string }) {
  const words = text.split(" ");
  return (
    <p className={styles.personaText}>
      {words.map((word, i) => (
        <motion.span
          key={i}
          className={styles.word}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 + i * 0.025, duration: 0.2 }}
        >
          {word}{" "}
        </motion.span>
      ))}
    </p>
  );
}


export function AIInsightCards({ developer, stats }: Props) {
  const { skill_scores, ai_persona } = developer;

  const langEntries = Object.entries(stats.language_percentages)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);

  if (langEntries.length === 0 && !ai_persona && !skill_scores) return null;

  const hasAI = Boolean(skill_scores && Object.keys(skill_scores).length > 0);

  const radarData = hasAI
    ? {
        axes: Object.entries(skill_scores!).map(([label, score]) => ({ label, score })),
        summary: ai_persona ?? "",
      }
    : null;

  return (
    <motion.section
      className={styles.section}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut", delay: 0.1 }}
    >
      {/* Section label */}
      <div className={styles.sectionHeader}>
        <Sparkles size={14} className={styles.sectionIcon} />
        <span className={styles.sectionLabel}>
          {hasAI ? "AI Analysis" : "Developer Snapshot"}
        </span>
        {hasAI && <span className={styles.aiPill}>powered by Groq</span>}
      </div>

      <div className={styles.grid}>
        {/* Left: SkillRadar (AI) OR language bars */}
        <div className={styles.card}>
          {radarData ? (
            <>
              <div className={styles.cardTitleRow}>
                <Sparkles size={15} className={styles.cardIcon} />
                <p className={styles.cardTitle}>Skill Radar</p>
              </div>
              <SkillRadar data={radarData} />
            </>
          ) : (
            <>
              <div className={styles.cardTitleRow}>
                <Code2 size={15} className={styles.cardIcon} />
                <p className={styles.cardTitle}>Languages</p>
              </div>

              {/* Language strip */}
              <div className={styles.langStrip}>
                {langEntries.map(([lang]) => (
                  <div
                    key={lang}
                    className={styles.langSegment}
                    style={{
                      flex: stats.language_percentages[lang],
                      backgroundColor: getLangColor(lang),
                    }}
                    title={`${lang}: ${Math.round(stats.language_percentages[lang])}%`}
                  />
                ))}
              </div>

              <div className={styles.langList}>
                {langEntries.map(([lang, pct], i) => (
                  <motion.div
                    key={lang}
                    className={styles.langRow}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 + i * 0.06 }}
                  >
                    <span
                      className={styles.langDot}
                      style={{ backgroundColor: getLangColor(lang) }}
                    />
                    <span className={styles.langName}>{lang}</span>
                    <div className={styles.langTrack}>
                      <motion.div
                        className={styles.langFill}
                        style={{ backgroundColor: getLangColor(lang) }}
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ delay: 0.2 + i * 0.06, duration: 0.6, ease: "easeOut" }}
                      />
                    </div>
                    <span className={styles.langPct}>{Math.round(pct)}%</span>
                  </motion.div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Right: AI persona OR code quality */}
        <div className={styles.card}>
          {ai_persona ? (
            <>
              <div className={styles.cardTitleRow}>
                <Sparkles size={15} className={styles.cardIcon} />
                <p className={styles.cardTitle}>Developer Persona</p>
              </div>
              <RevealText text={ai_persona} />
            </>
          ) : (
            <>
              <div className={styles.cardTitleRow}>
                <Activity size={15} className={styles.cardIcon} />
                <p className={styles.cardTitle}>Code Quality</p>
              </div>

              <div className={styles.qualityGrid}>
                {[
                  { value: stats.grade_counts?.A ?? 0, label: "A-grade repos", color: "var(--color-grade-a)" },
                  { value: stats.repos_with_tests, label: "have tests", color: "var(--color-accent)" },
                  { value: stats.repos_with_ci, label: "have CI/CD", color: "var(--color-info)" },
                  { value: Math.round(stats.avg_health_score), label: "avg health", color: "var(--color-grade-b)" },
                ].map(({ value, label, color }, i) => (
                  <motion.div
                    key={label}
                    className={styles.qualityStat}
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.15 + i * 0.08 }}
                  >
                    <span className={styles.qualityValue} style={{ color }}>
                      {formatNumber(value)}
                    </span>
                    <span className={styles.qualityLabel}>{label}</span>
                  </motion.div>
                ))}
              </div>

              {/* CI/test progress bars */}
              <div className={styles.qualityBars}>
                {[
                  { label: "Test coverage", value: stats.repos_with_tests, total: stats.total_repos },
                  { label: "CI enabled", value: stats.repos_with_ci, total: stats.total_repos },
                ].map(({ label, value, total }, i) => {
                  const pct = total > 0 ? (value / total) * 100 : 0;
                  return (
                    <div key={label} className={styles.qualityBar}>
                      <div className={styles.qualityBarHeader}>
                        <span className={styles.qualityBarLabel}>
                          <ShieldCheck size={12} style={{ color: "var(--color-accent)" }} />
                          {label}
                        </span>
                        <span className={styles.qualityBarPct}>{Math.round(pct)}%</span>
                      </div>
                      <div className={styles.barTrack}>
                        <motion.div
                          className={styles.barFill}
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ delay: 0.3 + i * 0.1, duration: 0.7, ease: "easeOut" }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {developer.peak_commit_day && (
                <p className={styles.commitNote}>
                  Most active on <strong>{developer.peak_commit_day}</strong>
                  {developer.commit_frequency_per_week != null &&
                    ` · ${developer.commit_frequency_per_week.toFixed(1)} commits/week`}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </motion.section>
  );
}
