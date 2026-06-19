import { motion } from "framer-motion";
import { CheckCircle2, XCircle, AlertCircle, ThumbsUp } from "lucide-react";
import styles from "./HireRecommendation.module.css";

type Verdict = "strong_yes" | "yes" | "maybe" | "no";
interface Props { data: { verdict: Verdict; headline: string; reasoning: string; strengths: string[]; gaps: string[] } }

const VERDICT_CONFIG: Record<Verdict, { label: string; color: string; icon: typeof ThumbsUp }> = {
  strong_yes: { label: "Strong Yes",  color: "var(--color-grade-a)", icon: ThumbsUp },
  yes:        { label: "Yes",          color: "var(--color-grade-a)", icon: CheckCircle2 },
  maybe:      { label: "Maybe",        color: "var(--color-grade-b)", icon: AlertCircle },
  no:         { label: "No",           color: "var(--color-grade-d)", icon: XCircle },
};

export function HireRecommendation({ data }: Props) {
  const { verdict = "maybe", headline, reasoning, strengths = [], gaps = [] } = data;
  const cfg = VERDICT_CONFIG[verdict] ?? VERDICT_CONFIG.maybe;
  const Icon = cfg.icon;

  return (
    <motion.div
      className={styles.container}
      style={{ borderLeftColor: cfg.color }}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className={styles.verdictRow}>
        <Icon size={20} style={{ color: cfg.color }} />
        <span className={styles.verdictLabel} style={{ color: cfg.color }}>{cfg.label}</span>
      </div>

      <p className={styles.headline}>{headline}</p>
      <p className={styles.reasoning}>{reasoning}</p>

      <div className={styles.columns}>
        {strengths.length > 0 && (
          <div className={styles.column}>
            <p className={styles.columnTitle}>Strengths</p>
            <ul className={styles.list}>
              {strengths.map((s, i) => (
                <li key={i} className={`${styles.listItem} ${styles.strength}`}>{s}</li>
              ))}
            </ul>
          </div>
        )}
        {gaps.length > 0 && (
          <div className={styles.column}>
            <p className={styles.columnTitle}>Gaps</p>
            <ul className={styles.list}>
              {gaps.map((g, i) => (
                <li key={i} className={`${styles.listItem} ${styles.gap}`}>{g}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </motion.div>
  );
}
