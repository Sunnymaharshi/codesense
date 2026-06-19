import { motion } from "framer-motion";
import styles from "./DeveloperPersona.module.css";

interface Trait { label: string; score: number; }
interface Props { data: { headline: string; summary: string; traits: Trait[] } }

export function DeveloperPersona({ data }: Props) {
  const { headline, summary, traits = [] } = data;

  return (
    <div className={styles.container}>
      <p className={styles.headline}>{headline}</p>
      <p className={styles.summary}>{summary}</p>
      <div className={styles.traits}>
        {traits.map((t, i) => (
          <motion.div
            key={t.label}
            className={styles.trait}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.06 }}
          >
            <div className={styles.traitHeader}>
              <span className={styles.traitLabel}>{t.label}</span>
              <span className={styles.traitScore}>{t.score}</span>
            </div>
            <div className={styles.traitTrack}>
              <motion.div
                className={styles.traitFill}
                style={{ backgroundColor: scoreColor(t.score) }}
                initial={{ width: 0 }}
                animate={{ width: `${t.score}%` }}
                transition={{ delay: 0.2 + i * 0.06, duration: 0.5, ease: "easeOut" }}
              />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function scoreColor(score: number): string {
  if (score >= 75) return "var(--color-grade-a)";
  if (score >= 50) return "var(--color-grade-b)";
  return "var(--color-grade-c)";
}
