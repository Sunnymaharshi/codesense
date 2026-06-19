import { motion, AnimatePresence } from "framer-motion";
import { Loader2, CheckCircle2 } from "lucide-react";
import { useProfileStore } from "@/store/profileStore";
import styles from "./IndexingProgress.module.css";

export function IndexingProgress() {
  const { indexStatus, reposDone, reposTotal } = useProfileStore();

  const isVisible = indexStatus === "pending" || indexStatus === "running";
  const isDone = indexStatus === "done";

  const pct =
    reposTotal > 0 ? Math.round((reposDone / reposTotal) * 100) : 0;

  return (
    <AnimatePresence>
      {(isVisible || isDone) && (
        <motion.div
          className={`${styles.banner} ${isDone ? styles.bannerDone : ""}`}
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <div className={styles.inner}>
            {/* Icon */}
            <div className={styles.iconWrap}>
              {isDone ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                >
                  <CheckCircle2 size={18} className={styles.iconDone} />
                </motion.div>
              ) : (
                <Loader2 size={18} className={styles.iconSpinner} />
              )}
            </div>

            {/* Text */}
            <div className={styles.text}>
              {isDone ? (
                <span className={styles.doneLabel}>
                  Indexed {reposTotal} {reposTotal === 1 ? "repo" : "repos"} — profile ready
                </span>
              ) : reposTotal > 0 ? (
                <span className={styles.label}>
                  Indexing{" "}
                  <strong>{reposDone}</strong> of{" "}
                  <strong>{reposTotal}</strong> repos…
                </span>
              ) : (
                <span className={styles.label}>Fetching repositories…</span>
              )}
            </div>

            {/* Progress bar */}
            {!isDone && reposTotal > 0 && (
              <div className={styles.barTrack}>
                <motion.div
                  className={styles.barFill}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              </div>
            )}

            {/* Percent */}
            {!isDone && reposTotal > 0 && (
              <span className={styles.pct}>{pct}%</span>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
