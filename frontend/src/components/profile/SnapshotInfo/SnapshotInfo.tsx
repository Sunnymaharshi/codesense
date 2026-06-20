import { useState } from "react";
import { RotateCw } from "lucide-react";
import { reindexUser } from "@/lib/api";
import { useProfileStore } from "@/store/profileStore";
import { timeAgo } from "@/lib/utils";
import styles from "./SnapshotInfo.module.css";

interface Props {
  username: string;
  indexedAt: string | null;
}

export function SnapshotInfo({ username, indexedAt }: Props) {
  const [reindexing, setReindexing] = useState(false);
  const { setIndexStatus, setProgress } = useProfileStore();

  async function handleReindex() {
    setReindexing(true);
    try {
      await reindexUser(username);
      setProgress(0, 0);
      setIndexStatus("pending");
    } finally {
      setReindexing(false);
    }
  }

  return (
    <div className={styles.row}>
      <span className={styles.label}>
        {indexedAt ? `Last indexed ${timeAgo(indexedAt)}` : "Not yet indexed"}
      </span>
      <button
        className={styles.btn}
        onClick={handleReindex}
        disabled={reindexing}
        aria-label="Re-index this developer"
      >
        <RotateCw size={12} className={reindexing ? styles.spinning : ""} />
        Re-index
      </button>
    </div>
  );
}
