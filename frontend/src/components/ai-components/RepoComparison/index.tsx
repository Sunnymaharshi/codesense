import { Badge } from "@/components/ui/Badge";
import { getLangColor } from "@/lib/utils";
import { CheckCircle2, XCircle } from "lucide-react";
import type { HealthGrade } from "@/lib/types";
import styles from "./RepoComparison.module.css";

interface RepoData { name: string; health_score: number; grade: string; stars: number; primary_language: string; has_tests: boolean; has_ci: boolean; }
interface Props { data: { repos: RepoData[] } }

const Signal = ({ active }: { active: boolean }) => active
  ? <CheckCircle2 size={13} style={{ color: "var(--color-grade-a)" }} />
  : <XCircle size={13} style={{ color: "var(--color-fg-subtle)", opacity: 0.4 }} />;

export function RepoComparison({ data }: Props) {
  const { repos = [] } = data;

  return (
    <div className={styles.container}>
      {repos.map((repo) => (
        <div key={repo.name} className={styles.card}>
          <div className={styles.header}>
            <span className={styles.name}>{repo.name.split("/").pop()}</span>
            <Badge grade={(repo.grade || "C") as HealthGrade} size="sm" />
          </div>
          <div className={styles.score}>{repo.health_score}<span className={styles.scoreMax}>/100</span></div>
          <div className={styles.meta}>
            {repo.primary_language && (
              <span className={styles.lang}>
                <span className={styles.langDot} style={{ backgroundColor: getLangColor(repo.primary_language) }} />
                {repo.primary_language}
              </span>
            )}
            <span className={styles.stars}>★ {repo.stars}</span>
          </div>
          <div className={styles.signals}>
            <span className={styles.signal}><Signal active={repo.has_tests} /> Tests</span>
            <span className={styles.signal}><Signal active={repo.has_ci} /> CI</span>
          </div>
        </div>
      ))}
    </div>
  );
}
