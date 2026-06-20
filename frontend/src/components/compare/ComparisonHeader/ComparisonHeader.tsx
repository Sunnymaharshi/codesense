import { motion } from "framer-motion";
import type { DeveloperResponse } from "@/lib/types";
import styles from "./ComparisonHeader.module.css";

interface Props {
  left: DeveloperResponse;
  right: DeveloperResponse;
}

function DevCard({ dev, align }: { dev: DeveloperResponse; align: "left" | "right" }) {
  const avatarSrc = dev.avatar_url ?? `https://avatars.dicebear.com/api/identicon/${dev.github_username}.svg`;
  return (
    <div className={`${styles.card} ${styles[align]}`}>
      <img src={avatarSrc} alt={dev.github_username} className={styles.avatar} width={64} height={64} />
      <div className={styles.info}>
        <span className={styles.name}>{dev.display_name ?? dev.github_username}</span>
        <a
          href={`https://github.com/${dev.github_username}`}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.handle}
        >
          @{dev.github_username}
        </a>
      </div>
    </div>
  );
}

export function ComparisonHeader({ left, right }: Props) {
  return (
    <motion.div
      className={styles.row}
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <DevCard dev={left} align="left" />
      <span className={styles.vs}>vs</span>
      <DevCard dev={right} align="right" />
    </motion.div>
  );
}
