import { useQuery } from "@tanstack/react-query";
import { listSnapshots } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import styles from "./SnapshotHistory.module.css";

interface Props {
  username: string;
}

export function SnapshotHistory({ username }: Props) {
  const { data } = useQuery({
    queryKey: ["snapshots", username],
    queryFn: () => listSnapshots(username),
    staleTime: 1000 * 60 * 5,
  });

  const snapshots = data?.snapshots ?? [];

  // Only show when there's meaningful history to display
  if (snapshots.length < 2) return null;

  const visible = snapshots.slice(0, 5);

  return (
    <div className={styles.container}>
      <h3 className={styles.heading}>Snapshot history</h3>
      <ol className={styles.list}>
        {visible.map((snap, i) => (
          <li key={snap.id} className={styles.item}>
            <div className={styles.dot} data-current={i === 0} />
            <div className={styles.content}>
              <span className={styles.time}>{timeAgo(snap.taken_at)}</span>
              <span className={styles.meta}>
                {snap.total_repos} repos · {snap.avg_health_score.toFixed(0)} avg score
              </span>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
