import { motion } from "framer-motion";
import type { DeveloperResponse } from "@/lib/types";
import styles from "./ProfileHeader.module.css";

interface ProfileHeaderProps {
  developer: DeveloperResponse;
}

export function ProfileHeader({ developer }: ProfileHeaderProps) {
  const avatarSrc =
    developer.avatar_url ??
    `https://avatars.dicebear.com/api/identicon/${developer.github_username}.svg`;

  return (
    <motion.header
      className={styles.header}
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <img
        src={avatarSrc}
        alt={`${developer.github_username} avatar`}
        className={styles.avatar}
        width={80}
        height={80}
      />

      <div className={styles.info}>
        <div className={styles.nameRow}>
          {developer.display_name && (
            <h1 className={styles.displayName}>{developer.display_name}</h1>
          )}
          <a
            href={`https://github.com/${developer.github_username}`}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.handle}
          >
            @{developer.github_username}
          </a>
        </div>

        {developer.bio && (
          <p className={styles.bio}>{developer.bio}</p>
        )}

        {developer.ai_persona && (
          <p className={styles.persona}>{developer.ai_persona}</p>
        )}
      </div>
    </motion.header>
  );
}
