import { useEffect } from "react";
import { useParams, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { getProfile } from "@/lib/api";
import { useProfileStore } from "@/store/profileStore";
import { useIndexingProgress } from "@/hooks/useIndexingProgress";
import { ProfileHeader } from "@/components/profile/ProfileHeader";
import { StatsRow } from "@/components/profile/StatsRow";
import { LanguageBars } from "@/components/profile/LanguageBars";
import { RepoGrid } from "@/components/profile/RepoGrid";
import { ContributionStats } from "@/components/profile/ContributionStats";
import { IndexingProgress } from "@/components/profile/IndexingProgress";
import {
  ProfileHeaderSkeleton,
  StatsRowSkeleton,
  RepoGridSkeleton,
} from "@/components/ui/Skeleton";
import styles from "./Profile.module.css";

export function Profile() {
  const { username } = useParams({ from: "/u/$username" });
  const { setUsername, indexStatus } = useProfileStore();

  useEffect(() => {
    setUsername(username);
  }, [username, setUsername]);

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["profile", username],
    queryFn: () => getProfile(username),
    retry: 2,
    // While indexing, poll every 3s as a fallback even without WS
    refetchInterval: indexStatus === "running" ? 3000 : false,
  });

  // Connect WebSocket — drives store progress + triggers refetch on done
  useIndexingProgress(username, {
    onDone: () => {
      // Small delay so Postgres has committed before we fetch
      setTimeout(() => refetch(), 500);
    },
  });

  const showSkeleton = isLoading && !data;
  const showProfile = !!data;

  return (
    <div className={styles.page}>
      {/* Nav */}
      <nav className={styles.nav}>
        <Link to="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          codesense
        </Link>
        {data && (
          <a
            href={`https://github.com/${username}`}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.ghLink}
          >
            github.com/{username}
          </a>
        )}
      </nav>

      <div className={styles.container}>
        {/* Live indexing progress banner */}
        <IndexingProgress />

        <AnimatePresence mode="wait">
          {showSkeleton && (
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
                <RefreshCw size={14} />
                Try again
              </button>
            </motion.div>
          )}

          {showProfile && (
            <motion.div
              key="profile"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              <ProfileHeader developer={data.developer} />

              <div className={styles.statsSection}>
                <StatsRow stats={data.stats} />
              </div>

              <div className={styles.columns}>
                <div className={styles.sidebar}>
                  <LanguageBars stats={data.stats} />
                  <ContributionStats
                    developer={data.developer}
                    stats={data.stats}
                  />
                </div>
                <div className={styles.main}>
                  <RepoGrid repos={data.repos} />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
