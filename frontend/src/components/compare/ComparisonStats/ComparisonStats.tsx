import { motion } from "framer-motion";
import type { ProfileStatsResponse } from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import styles from "./ComparisonStats.module.css";

interface Props {
  left: ProfileStatsResponse;
  right: ProfileStatsResponse;
  leftName: string;
  rightName: string;
}

interface Row { label: string; leftVal: number; rightVal: number; format?: (n: number) => string; }

export function ComparisonStats({ left, right, leftName, rightName }: Props) {
  const rows: Row[] = [
    { label: "Repositories", leftVal: left.total_repos, rightVal: right.total_repos },
    { label: "Avg health score", leftVal: left.avg_health_score, rightVal: right.avg_health_score },
    {
      label: "A-grade repos",
      leftVal: left.grade_counts?.A ?? 0,
      rightVal: right.grade_counts?.A ?? 0,
    },
  ];

  return (
    <div className={styles.container}>
      {rows.map((row, i) => {
        const leftWins = row.leftVal > row.rightVal;
        const rightWins = row.rightVal > row.leftVal;
        const max = Math.max(row.leftVal, row.rightVal, 1);

        return (
          <motion.div
            key={row.label}
            className={styles.row}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.08 }}
          >
            <div className={styles.side}>
              <span className={`${styles.value} ${leftWins ? styles.winner : ""}`}>
                {row.format ? row.format(row.leftVal) : formatNumber(row.leftVal)}
              </span>
              <div className={styles.barTrack}>
                <motion.div
                  className={`${styles.barFill} ${styles.barLeft} ${leftWins ? styles.barWin : ""}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${(row.leftVal / max) * 100}%` }}
                  transition={{ delay: 0.2 + i * 0.08, duration: 0.4 }}
                />
              </div>
            </div>

            <span className={styles.label}>{row.label}</span>

            <div className={styles.side}>
              <div className={styles.barTrack}>
                <motion.div
                  className={`${styles.barFill} ${styles.barRight} ${rightWins ? styles.barWin : ""}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${(row.rightVal / max) * 100}%` }}
                  transition={{ delay: 0.2 + i * 0.08, duration: 0.4 }}
                  style={{ marginLeft: "auto" }}
                />
              </div>
              <span className={`${styles.value} ${rightWins ? styles.winner : ""}`}>
                {row.format ? row.format(row.rightVal) : formatNumber(row.rightVal)}
              </span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
