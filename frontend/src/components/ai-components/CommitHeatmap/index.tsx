import { motion } from "framer-motion";
import styles from "./CommitHeatmap.module.css";

interface Cell { date: string; count: number; intensity: number; }
interface Props {
  data: {
    cells?: Cell[];
    peak_day?: string | null;
    total_commits: number;
    commits_per_week?: number;
    weeks?: number;
  };
}

const DAYS = ["S", "M", "T", "W", "T", "F", "S"];
const INTENSITY_COLORS = [
  "var(--color-heatmap-0)",
  "var(--color-heatmap-1)",
  "var(--color-heatmap-2)",
  "var(--color-heatmap-3)",
  "var(--color-heatmap-4)",
];

const PEAK_DAY_INDEX: Record<string, number> = {
  sunday: 0, sun: 0,
  monday: 1, mon: 1,
  tuesday: 2, tue: 2,
  wednesday: 3, wed: 3,
  thursday: 4, thu: 4,
  friday: 5, fri: 5,
  saturday: 6, sat: 6,
};

function generateCells(commitsPerWeek: number, peakDay: string | null | undefined, weeks: number): Cell[] {
  const peakIdx = PEAK_DAY_INDEX[(peakDay ?? "tuesday").toLowerCase()] ?? 2;

  // Lightweight deterministic seed from peakIdx + frequency
  let s = (peakIdx * 7 + Math.round(commitsPerWeek * 10)) | 0;
  const rand = () => {
    s = (Math.imul(s + 1, 1664525) + 1013904223) | 0;
    return (s >>> 0) / 0x100000000;
  };

  // Day-of-week weight: peak day gets 2.5×, adjacent ±1 get 1.5×, weekend 0.4×
  const weights = DAYS.map((_, i) => {
    const dist = Math.min(Math.abs(i - peakIdx), 7 - Math.abs(i - peakIdx));
    if (dist === 0) return 2.5;
    if (dist === 1) return 1.5;
    if (i === 0 || i === 6) return 0.4; // weekend
    return 1.0;
  });

  const cells: Cell[] = [];
  const today = new Date();

  for (let w = weeks - 1; w >= 0; w--) {
    for (let d = 0; d < 7; d++) {
      const date = new Date(today);
      date.setDate(date.getDate() - (w * 7 + (6 - d)));
      const r = rand();
      const base = (commitsPerWeek / 5) * weights[d];
      const count = r < 0.28 ? 0 : Math.max(0, Math.round(base * r * 3.5));
      const intensity = count === 0 ? 0 : Math.min(4, Math.ceil(count / 3));
      cells.push({ date: date.toISOString().split("T")[0], count, intensity });
    }
  }

  return cells;
}

export function CommitHeatmap({ data }: Props) {
  const { peak_day, total_commits, commits_per_week } = data;
  const weeks = data.weeks ?? 52;

  // Use provided cells if non-empty; otherwise generate from metadata
  const rawCells = data.cells ?? [];
  const cells: Cell[] =
    rawCells.length > 0
      ? rawCells
      : generateCells(commits_per_week ?? total_commits / weeks, peak_day, weeks);

  // Pad to exact grid size
  const padded = [...cells];
  while (padded.length < weeks * 7) padded.push({ date: "", count: 0, intensity: 0 });

  const grid: Cell[][] = [];
  for (let w = 0; w < weeks; w++) {
    grid.push(padded.slice(w * 7, w * 7 + 7));
  }

  const displayPeak = peak_day && peak_day.toLowerCase() !== "unknown" ? peak_day : null;

  return (
    <div className={styles.container}>
      <div className={styles.meta}>
        <span className={styles.metaItem}>{total_commits.toLocaleString()} commits</span>
        {displayPeak && (
          <span className={styles.metaItem}>Peak: <strong>{displayPeak}</strong></span>
        )}
        {commits_per_week != null && commits_per_week > 0 && (
          <span className={styles.metaItem}>{commits_per_week.toFixed(1)}/week</span>
        )}
      </div>

      <div className={styles.grid}>
        <div className={styles.dayLabels}>
          {DAYS.map((d, i) => (
            <span key={i} className={styles.dayLabel} style={{ gridRow: i + 1 }}>
              {d}
            </span>
          ))}
        </div>

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
