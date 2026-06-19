import styles from "./Skeleton.module.css";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  className?: string;
}

export function Skeleton({
  width,
  height = "1em",
  borderRadius,
  className,
}: SkeletonProps) {
  return (
    <span
      className={`${styles.skeleton} shimmer ${className ?? ""}`}
      style={{
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
        borderRadius,
        display: "inline-block",
      }}
      aria-hidden="true"
    />
  );
}

/* ─── Composed skeletons ─────────────────────────────────── */
export function ProfileHeaderSkeleton() {
  return (
    <div className={styles.headerSkeleton}>
      <Skeleton width={80} height={80} borderRadius="50%" />
      <div className={styles.headerText}>
        <Skeleton width={200} height={28} />
        <Skeleton width={140} height={18} />
        <Skeleton width={320} height={16} />
      </div>
    </div>
  );
}

export function StatsRowSkeleton() {
  return (
    <div className={styles.statsRow}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className={styles.statCard}>
          <Skeleton width={60} height={32} />
          <Skeleton width={80} height={14} />
        </div>
      ))}
    </div>
  );
}

export function RepoCardSkeleton() {
  return (
    <div className={styles.repoCard}>
      <div className={styles.repoCardHeader}>
        <Skeleton width="60%" height={18} />
        <Skeleton width={28} height={22} />
      </div>
      <Skeleton width="90%" height={14} />
      <Skeleton width="75%" height={14} />
      <div className={styles.repoCardFooter}>
        <Skeleton width={60} height={14} />
        <Skeleton width={50} height={14} />
        <Skeleton width={50} height={14} />
      </div>
    </div>
  );
}

export function RepoGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className={styles.repoGrid}>
      {Array.from({ length: count }).map((_, i) => (
        <RepoCardSkeleton key={i} />
      ))}
    </div>
  );
}
