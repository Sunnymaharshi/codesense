import { motion } from "framer-motion";
import { getLangColor } from "@/lib/utils";
import styles from "./GrowthTimeline.module.css";

interface Milestone { year: number; tech: string; description: string; repo?: string; }
interface Props { data: { milestones: Milestone[] } }

export function GrowthTimeline({ data }: Props) {
  const { milestones = [] } = data;
  const sorted = [...milestones].sort((a, b) => a.year - b.year);

  return (
    <div className={styles.container}>
      {sorted.map((m, i) => (
        <motion.div
          key={i}
          className={styles.item}
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.08, duration: 0.3 }}
        >
          <div className={styles.spine}>
            <div
              className={styles.dot}
              style={{ backgroundColor: getLangColor(m.tech) }}
            />
            {i < sorted.length - 1 && <div className={styles.line} />}
          </div>
          <div className={styles.content}>
            <div className={styles.header}>
              <span className={styles.year}>{m.year}</span>
              <span
                className={styles.tech}
                style={{ color: getLangColor(m.tech), borderColor: getLangColor(m.tech) + "33" }}
              >
                {m.tech}
              </span>
            </div>
            <p className={styles.description}>{m.description}</p>
            {m.repo && <span className={styles.repo}>{m.repo}</span>}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
