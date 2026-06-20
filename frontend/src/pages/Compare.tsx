import { useParams, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { compareProfiles } from "@/lib/api";
import { ComparisonHeader } from "@/components/compare/ComparisonHeader";
import { ComparisonStats } from "@/components/compare/ComparisonStats";
import { RepoGrid } from "@/components/profile/RepoGrid";
import { Skeleton } from "@/components/ui/Skeleton";
import styles from "./Compare.module.css";

export function Compare() {
  const { user1, user2 } = useParams({ from: "/compare/$user1/$user2" });

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["compare", user1, user2],
    queryFn: () => compareProfiles(user1, user2),
    retry: 1,
  });

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          codesense
        </Link>
      </nav>

      <div className={styles.container}>
        <AnimatePresence mode="wait">
          {isLoading && (
            <motion.div key="skeleton" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className={styles.headerSkeleton}>
                <Skeleton width={64} height={64} borderRadius="50%" />
                <Skeleton width={40} height={20} />
                <Skeleton width={64} height={64} borderRadius="50%" />
              </div>
              <Skeleton width="100%" height={180} />
            </motion.div>
          )}

          {isError && (
            <motion.div key="error" className={styles.errorState} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <p className={styles.errorTitle}>Couldn't load comparison</p>
              <p className={styles.errorMsg}>
                {error instanceof Error ? error.message : "Both developers need to be analyzed first."}
              </p>
              <button className={styles.retryBtn} onClick={() => refetch()}>
                <RefreshCw size={14} /> Try again
              </button>
            </motion.div>
          )}

          {data && (
            <motion.div key="compare" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
              <ComparisonHeader left={data.left.developer} right={data.right.developer} />

              <div className={styles.statsSection}>
                <ComparisonStats
                  left={data.left.stats}
                  right={data.right.stats}
                  leftName={data.left.developer.github_username}
                  rightName={data.right.developer.github_username}
                />
              </div>

              <div className={styles.reposColumns}>
                <div className={styles.repoColumn}>
                  <h3 className={styles.repoColumnTitle}>{data.left.developer.github_username}</h3>
                  <RepoGrid repos={data.left.repos.slice(0, 6)} />
                </div>
                <div className={styles.repoColumn}>
                  <h3 className={styles.repoColumnTitle}>{data.right.developer.github_username}</h3>
                  <RepoGrid repos={data.right.repos.slice(0, 6)} />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
