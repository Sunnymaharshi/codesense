import { motion } from "framer-motion";
import styles from "./CommitHeatmap.module.css";

interface Cell { date: string; count: number; intensity: number; }
interface Props { data: { cells: Cell[]; peak_day: string; total_commits: number; weeks?: number } }

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const INTENSITY_COLORS = [
  "var(--color-heatmap-0)",
  "var(--color-heatmap-1)",
  "var(--color-heatmap-2)",
  "var(--color-heatmap-3)",
  "var(--color-heatmap-4)",
];

export function CommitHeatmap({ data }: Props) {
  const { cells = [], peak_day, total_commits } = data;
  const weeks = data.weeks ?? 52;

  // Pad cells to fill grid
  const padded = [...cells];
  while (padded.length < weeks * 7) padded.push({ date: "", count: 0, intensity: 0 });

  const grid: Cell[][] = [];
  for (let w = 0; w < weeks; w++) {
    grid.push(padded.slice(w * 7, w * 7 + 7));
  }

  return (
    <div className={styles.container}>
      <div className={styles.meta}>
        <span className={styles.metaItem}>{total_commits.toLocaleString()} commits</span>
        {peak_day && <span className={styles.metaItem}>Peak: <strong>{peak_day}</strong></span>}
      </div>

      <div className={styles.grid}>
        {/* Day labels */}
        <div className={styles.dayLabels}>
          {DAYS.map((d, i) => (
            <span key={d} className={styles.dayLabel} style={{ gridRow: i + 1 }}>{i % 2 === 1 ? d : ""}</span>
          ))}
        </div>

        {/* Cells */}
        <div className={styles.cells}>
          {grid.map((week, wi) => (
            <div key={wi} className={styles.week}>
              {week.map((cell, di) => (
                <motion.div
                  key={`${wi}-${di}`}
                  className={styles.cell}
                  style={{ backgroundColor: INTENSITY_COLORS[Math.min(cell.intensity, 4)] }}
                  title={cell.date ? `${cell.date}: ${cell.count} commits` : ""}
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: wi * 0.005, duration: 0.15 }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className={styles.legend}>
        <span className={styles.legendLabel}>Less</span>
        {INTENSITY_COLORS.map((c, i) => (
          <div key={i} className={styles.legendCell} style={{ backgroundColor: c }} />
        ))}
        <span className={styles.legendLabel}>More</span>
      </div>
    </div>
  );
}
