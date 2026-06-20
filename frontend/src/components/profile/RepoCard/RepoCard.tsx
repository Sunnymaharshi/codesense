import { motion } from "framer-motion";
import { Star, GitFork, GitCommit, CheckCircle2, XCircle } from "lucide-react";
import type { RepoResponse } from "@/lib/types";
import { getLangColor, formatNumber, timeAgo } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import styles from "./RepoCard.module.css";

interface SignalPillProps {
  label: string;
  active: boolean;
}

function SignalPill({ label, active }: SignalPillProps) {
  return (
    <span className={`${styles.pill} ${active ? styles.pillActive : styles.pillInactive}`}>
      {active ? (
        <CheckCircle2 size={11} className={styles.pillIcon} />
      ) : (
        <XCircle size={11} className={styles.pillIcon} />
      )}
      {label}
    </span>
  );
}

interface RepoCardProps {
  repo: RepoResponse;
  index?: number;
}

export function RepoCard({ repo, index = 0 }: RepoCardProps) {
  return (
    <motion.article
      className={styles.card}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.04, 0.4) }}
      whileHover={{ y: -2, transition: { duration: 0.15 } }}
    >
      {/* Header */}
      <div className={styles.header}>
        <a
          href={repo.github_url ?? `https://github.com/${repo.full_name}`}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.repoName}
        >
          {repo.name}
        </a>
        <Badge grade={repo.health_grade} size="sm" />
      </div>

      {/* Description */}
      {repo.description && (
        <p className={styles.description}>{repo.description}</p>
      )}

      {/* Signal pills */}
      <div className={styles.signals}>
        <SignalPill label="README" active={repo.has_readme} />
        <SignalPill label="Tests" active={repo.has_tests} />
        <SignalPill label="CI" active={repo.has_ci} />
        <SignalPill label="Docker" active={repo.has_docker} />
        <SignalPill label="License" active={repo.has_license} />
      </div>

      {/* Footer meta */}
      <footer className={styles.footer}>
        {repo.primary_language && (
          <span className={styles.lang}>
            <span
              className={styles.langDot}
              style={{ backgroundColor: getLangColor(repo.primary_language) }}
            />
            {repo.primary_language}
          </span>
        )}
        {repo.stars > 0 && (
          <span className={styles.meta}>
            <Star size={13} /> {formatNumber(repo.stars)}
          </span>
        )}
        {repo.forks > 0 && (
          <span className={styles.meta}>
            <GitFork size={13} /> {formatNumber(repo.forks)}
          </span>
        )}
        {repo.commit_count > 0 && (
          <span className={styles.meta}>
            <GitCommit size={13} /> {formatNumber(repo.commit_count)}
          </span>
        )}
        {repo.last_commit_at && (
          <span className={styles.lastCommit}>
            {timeAgo(repo.last_commit_at)}
          </span>
        )}
      </footer>
    </motion.article>
  );
}
