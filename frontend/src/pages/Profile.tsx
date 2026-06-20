import { useEffect } from "react";
import { useParams, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { getProfile } from "@/lib/api";
import { useProfileStore } from "@/store/profileStore";
import { useChatStore } from "@/store/chatStore";
import { useIndexingProgress } from "@/hooks/useIndexingProgress";
import { useProfileMeta } from "@/hooks/useProfileMeta";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { AIInsightCards } from "@/components/profile/AIInsightCards";
import { ProfileAIShowcase } from "@/components/profile/ProfileAIShowcase";
import { RepoGrid } from "@/components/profile/RepoGrid";
import { IndexingProgress } from "@/components/profile/IndexingProgress";
import { SnapshotInfo } from "@/components/profile/SnapshotInfo";
import { CompareEntry } from "@/components/profile/CompareEntry";
import { InlineChatPanel } from "@/components/chat/InlineChatPanel";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import {
  ProfileHeaderSkeleton,
  StatsRowSkeleton,
  RepoGridSkeleton,
} from "@/components/ui/Skeleton";
import styles from "./Profile.module.css";

export function Profile() {
  const { username } = useParams({ from: "/u/$username" });
  const { setUsername, indexStatus } = useProfileStore();
  const clearChat = useChatStore((s) => s.clear);

  useEffect(() => {
    setUsername(username);
    clearChat();
  }, [username, setUsername, clearChat]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["profile", username],
    queryFn: () => getProfile(username),
    retry: 2,
    refetchInterval: indexStatus === "running" || indexStatus === "pending" ? 3000 : false,
  });

  useIndexingProgress(username, {
    onDone: () => setTimeout(() => refetch(), 500),
    onAgentDone: () => setTimeout(() => refetch(), 500),
  });

  useProfileMeta(data);

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          codesense
        </Link>
        <div className={styles.navRight}>
          {data && <CompareEntry username={username} />}
          {data?.developer.skill_scores && (
            <span className={styles.aiAnalyzedBadge} title="AI analysis complete">
              AI analyzed
            </span>
          )}
          <ThemeToggle />
        </div>
      </nav>

      <div className={styles.layout}>
        {/* ── Left: profile content ─────────────────────── */}
        <div className={styles.profileCol}>
          <IndexingProgress />

          <AnimatePresence mode="wait">
            {isLoading && !data && (
              <motion.div
                key="skeleton"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <ProfileHeaderSkeleton />
                <StatsRowSkeleton />
                <div style={{ marginTop: "var(--space-8)" }}>
                  <RepoGridSkeleton count={6} />
                </div>
              </motion.div>
            )}

            {isError && !data && (
              <motion.div
                key="error"
                className={styles.errorState}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <p className={styles.errorTitle}>Failed to load profile</p>
                <p className={styles.errorMsg}>
                  {error instanceof Error ? error.message : "Unknown error"}
                </p>
                <button className={styles.retryBtn} onClick={() => refetch()}>
                  <RefreshCw size={14} /> Try again
                </button>
              </motion.div>
            )}

            {data && (
              <motion.div
                key="profile"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                <div className={styles.headerMeta}>
                  <SnapshotInfo
                    username={username}
                    indexedAt={data.developer.indexed_at}
                  />
                </div>

                <ProfileHeader developer={data.developer} stats={data.stats} />
                <AIInsightCards developer={data.developer} stats={data.stats} />
                <ProfileAIShowcase
                  developer={data.developer}
                  stats={data.stats}
                  repos={data.repos}
                />

                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25, duration: 0.4 }}
                >
                  <RepoGrid repos={data.repos} />
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Right: AI chat — always visible ──────────── */}
        <aside className={styles.chatCol}>
          {data ? (
            <InlineChatPanel username={username} />
          ) : (
            <div className={styles.chatPlaceholder}>
              <div className={styles.chatPlaceholderInner}>
                <div className={styles.chatPlaceholderIcon}>✦</div>
                <p className={styles.chatPlaceholderText}>
                  Loading profile to enable AI chat…
                </p>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
