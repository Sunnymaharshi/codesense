import { motion } from "framer-motion";
import { GitFork, Star, GitCommit, FolderGit2 } from "lucide-react";
import type { DeveloperResponse, ProfileStatsResponse } from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import styles from "./ProfileHeader.module.css";

interface ProfileHeaderProps {
  developer: DeveloperResponse;
  stats: ProfileStatsResponse;
}

export function ProfileHeader({ developer, stats }: ProfileHeaderProps) {
  const avatarSrc =
    developer.avatar_url ??
    `https://api.dicebear.com/7.x/identicon/svg?seed=${developer.github_username}`;

  return (
    <motion.div
      className={styles.hero}
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
    >
      <div className={styles.glow} />

      <div className={styles.inner}>
        <div className={styles.avatarWrap}>
          <div className={styles.avatarRing} />
          <img
            src={avatarSrc}
            alt={developer.github_username}
            className={styles.avatar}
            width={96}
            height={96}
          />
        </div>

        <div className={styles.info}>
          <div className={styles.nameRow}>
            <h1 className={styles.name}>
              {developer.display_name ?? developer.github_username}
            </h1>
            <a
              href={`https://github.com/${developer.github_username}`}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.handle}
            >
              @{developer.github_username}
            </a>
          </div>

          {developer.bio && <p className={styles.bio}>{developer.bio}</p>}

          <div className={styles.chips}>
            <span className={styles.chip}>
              <FolderGit2 size={13} />
              {stats.total_repos} repos
            </span>
            <span className={styles.chip}>
              <Star size={13} />
              {formatNumber(stats.total_stars)} stars
            </span>
            <span className={styles.chip}>
              <GitFork size={13} />
              {formatNumber(stats.total_forks)} forks
            </span>
            <span className={styles.chip}>
              <GitCommit size={13} />
              {formatNumber(stats.total_commits)} commits
            </span>
            {stats.primary_language && (
              <span className={`${styles.chip} ${styles.chipAccent}`}>
                {stats.primary_language}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
