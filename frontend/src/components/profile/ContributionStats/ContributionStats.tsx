import { motion } from "framer-motion";
import { Calendar, Zap, TrendingUp } from "lucide-react";
import type { DeveloperResponse, ProfileStatsResponse } from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import styles from "./ContributionStats.module.css";

interface ContributionStatsProps {
  developer: DeveloperResponse;
  stats: ProfileStatsResponse;
}

export function ContributionStats({ developer, stats }: ContributionStatsProps) {
  const hasData =
    developer.peak_commit_day ||
    developer.commit_frequency_per_week ||
    stats.repos_with_tests > 0;

  if (!hasData) return null;

  return (
    <section className={styles.section}>
      <h2 className={styles.heading}>Contribution patterns</h2>
      <div className={styles.cards}>
        {developer.peak_commit_day && (
          <motion.div
            className={styles.card}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Calendar size={16} className={styles.icon} />
            <div>
              <div className={styles.cardValue}>{developer.peak_commit_day}</div>
              <div className={styles.cardLabel}>Peak commit day</div>
            </div>
          </motion.div>
        )}

        {developer.commit_frequency_per_week != null && (
          <motion.div
            className={styles.card}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <Zap size={16} className={styles.icon} />
            <div>
              <div className={styles.cardValue}>
                {developer.commit_frequency_per_week.toFixed(1)}
                <span className={styles.unit}>/wk</span>
              </div>
              <div className={styles.cardLabel}>Commit frequency</div>
            </div>
          </motion.div>
        )}

        <motion.div
          className={styles.card}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <TrendingUp size={16} className={styles.icon} />
          <div>
            <div className={styles.cardValue}>
              {formatNumber(stats.repos_with_tests)}
              <span className={styles.unit}> / {formatNumber(stats.total_repos)}</span>
            </div>
            <div className={styles.cardLabel}>Repos with tests</div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
