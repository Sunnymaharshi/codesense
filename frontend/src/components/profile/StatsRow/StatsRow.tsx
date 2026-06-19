import { motion } from "framer-motion";
import { Star, GitFork, GitCommit, FolderGit2, Activity } from "lucide-react";
import type { ProfileStatsResponse } from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import styles from "./StatsRow.module.css";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  index: number;
}

function StatCard({ label, value, icon, index }: StatCardProps) {
  return (
    <motion.div
      className={styles.card}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.06, ease: "easeOut" }}
    >
      <div className={styles.iconWrap}>{icon}</div>
      <span className={styles.value}>{value}</span>
      <span className={styles.label}>{label}</span>
    </motion.div>
  );
}

interface StatsRowProps {
  stats: ProfileStatsResponse;
}

export function StatsRow({ stats }: StatsRowProps) {
  const cards = [
    {
      label: "Repositories",
      value: formatNumber(stats.total_repos),
      icon: <FolderGit2 size={18} />,
    },
    {
      label: "Stars earned",
      value: formatNumber(stats.total_stars),
      icon: <Star size={18} />,
    },
    {
      label: "Forks",
      value: formatNumber(stats.total_forks),
      icon: <GitFork size={18} />,
    },
    {
      label: "Commits",
      value: formatNumber(stats.total_commits),
      icon: <GitCommit size={18} />,
    },
    {
      label: "Avg health",
      value: `${Math.round(stats.avg_health_score)}`,
      icon: <Activity size={18} />,
    },
  ];

  return (
    <div className={styles.row} role="list">
      {cards.map((card, i) => (
        <StatCard key={card.label} {...card} index={i} />
      ))}
    </div>
  );
}
