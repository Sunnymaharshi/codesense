import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, CheckCircle2, Sparkles } from "lucide-react";
import { useProfileStore } from "@/store/profileStore";
import styles from "./IndexingProgress.module.css";

const STEP_LABELS: Record<string, string> = {
  fetch:   "Fetching code samples",
  analyse: "Analyzing code patterns",
  persona: "Generating developer persona",
  score:   "Computing skill scores",
};

export function IndexingProgress() {
  const { indexStatus, reposDone, reposTotal, agentStatus, agentStep } =
    useProfileStore();

  const [dismissed, setDismissed] = useState(false);

  const isIndexing = indexStatus === "pending" || indexStatus === "running";
  const isAnalyzing = indexStatus === "done" && agentStatus === "running";
  const isFullyDone = indexStatus === "done" && agentStatus === "done";
  const isVisible = (isIndexing || isAnalyzing || isFullyDone) && !dismissed;

  // Auto-dismiss the "done" banner after 4 seconds
  useEffect(() => {
    if (!isFullyDone) return;
    const t = setTimeout(() => setDismissed(true), 4000);
    return () => clearTimeout(t);
  }, [isFullyDone]);

  // Reset dismissed when a new indexing run starts
  useEffect(() => {
    if (isIndexing) setDismissed(false);
  }, [isIndexing]);

  const pct = reposTotal > 0 ? Math.round((reposDone / reposTotal) * 100) : 0;
  const stepLabel = agentStep ? (STEP_LABELS[agentStep] ?? agentStep) : "Analyzing code";

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          className={`${styles.banner} ${isFullyDone ? styles.bannerDone : ""} ${isAnalyzing ? styles.bannerAnalyzing : ""}`}
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <div className={styles.inner}>
            {/* Icon */}
            <div className={styles.iconWrap}>
              {isFullyDone ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                >
                  <CheckCircle2 size={18} className={styles.iconDone} />
                </motion.div>
              ) : isAnalyzing ? (
                <Sparkles size={18} className={styles.iconAnalyzing} />
              ) : (
                <Loader2 size={18} className={styles.iconSpinner} />
              )}
            </div>

            {/* Text */}
            <div className={styles.text}>
              {isFullyDone ? (
                <span className={styles.doneLabel}>
                  Indexed {reposTotal} {reposTotal === 1 ? "repo" : "repos"} · AI analyzed
                </span>
              ) : isAnalyzing ? (
                <span className={styles.analyzingLabel}>
                  {stepLabel}
                  <span className={styles.ellipsis}>…</span>
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

            {/* Progress bar — only during repo indexing */}
            {isIndexing && reposTotal > 0 && (
              <div className={styles.barTrack}>
                <motion.div
                  className={styles.barFill}
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              </div>
            )}

            {isIndexing && reposTotal > 0 && (
              <span className={styles.pct}>{pct}%</span>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
