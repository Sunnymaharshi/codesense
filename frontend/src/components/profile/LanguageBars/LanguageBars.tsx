import { motion } from "framer-motion";
import type { ProfileStatsResponse } from "@/lib/types";
import { getLangColor } from "@/lib/utils";
import styles from "./LanguageBars.module.css";

interface LanguageBarsProps {
  stats: ProfileStatsResponse;
}

export function LanguageBars({ stats }: LanguageBarsProps) {
  const entries = Object.entries(stats.language_percentages)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8);

  if (entries.length === 0) return null;

  return (
    <section className={styles.section}>
      <h2 className={styles.heading}>Languages</h2>

      {/* Summary strip */}
      <div className={styles.strip} role="img" aria-label="Language distribution">
        {entries.map(([lang, pct]) => (
          <div
            key={lang}
            className={styles.stripSegment}
            style={{
              width: `${pct}%`,
              backgroundColor: getLangColor(lang),
            }}
            title={`${lang}: ${Math.round(pct)}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <ul className={styles.list}>
        {entries.map(([lang, pct], i) => (
          <motion.li
            key={lang}
            className={styles.item}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05, duration: 0.25 }}
          >
            <span
              className={styles.dot}
              style={{ backgroundColor: getLangColor(lang) }}
            />
            <span className={styles.langName}>{lang}</span>
            <div className={styles.barTrack}>
              <motion.div
                className={styles.barFill}
                style={{ backgroundColor: getLangColor(lang) }}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ delay: 0.2 + i * 0.05, duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <span className={styles.pct}>{Math.round(pct)}%</span>
          </motion.li>
        ))}
      </ul>
    </section>
  );
}
