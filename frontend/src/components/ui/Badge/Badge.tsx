import type { HealthGrade } from "@/lib/types";
import { getGradeColor, getGradeBg } from "@/lib/utils";
import styles from "./Badge.module.css";

interface BadgeProps {
  grade: HealthGrade;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function Badge({ grade, size = "md", showLabel = false }: BadgeProps) {
  return (
    <span
      className={`${styles.badge} ${styles[size]}`}
      style={{
        color: getGradeColor(grade),
        backgroundColor: getGradeBg(grade),
        borderColor: getGradeColor(grade),
      }}
    >
      {grade}
      {showLabel && <span className={styles.label}>health</span>}
    </span>
  );
}
