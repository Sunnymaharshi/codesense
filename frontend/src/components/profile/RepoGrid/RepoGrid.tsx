import { useState } from "react";
import type { RepoResponse } from "@/lib/types";
import { RepoCard } from "@/components/profile/RepoCard";
import styles from "./RepoGrid.module.css";

type SortKey = "health" | "stars" | "commits" | "recent";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "health", label: "Health" },
  { key: "stars", label: "Stars" },
  { key: "commits", label: "Commits" },
  { key: "recent", label: "Recent" },
];

function sortRepos(repos: RepoResponse[], key: SortKey): RepoResponse[] {
  return [...repos].sort((a, b) => {
    switch (key) {
      case "health": return b.health_score - a.health_score;
      case "stars": return b.stars - a.stars;
      case "commits": return b.commit_count - a.commit_count;
      case "recent": {
        const ta = a.last_commit_at ? new Date(a.last_commit_at).getTime() : 0;
        const tb = b.last_commit_at ? new Date(b.last_commit_at).getTime() : 0;
        return tb - ta;
      }
    }
  });
}

interface RepoGridProps {
  repos: RepoResponse[];
}

export function RepoGrid({ repos }: RepoGridProps) {
  const [sortKey, setSortKey] = useState<SortKey>("health");
  const sorted = sortRepos(repos, sortKey);

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <h2 className={styles.heading}>
          Repositories
          <span className={styles.count}>{repos.length}</span>
        </h2>
        <div className={styles.sortRow} role="group" aria-label="Sort repositories">
          {SORT_OPTIONS.map(({ key, label }) => (
            <button
              key={key}
              className={`${styles.sortBtn} ${sortKey === key ? styles.sortBtnActive : ""}`}
              onClick={() => setSortKey(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.grid}>
        {sorted.map((repo, i) => (
          <RepoCard key={repo.id} repo={repo} index={i} />
        ))}
      </div>
    </section>
  );
}
