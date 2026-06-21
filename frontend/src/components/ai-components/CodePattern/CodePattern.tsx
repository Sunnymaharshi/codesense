import { useEffect, useState } from "react";
import { codeToHtml } from "shiki";
import styles from "./CodePattern.module.css";

interface CodePatternData {
  file_path: string;
  language: string;
  snippet: string;
  insight: string;
}

export function CodePattern({ data }: { data: CodePatternData }) {
  const [highlighted, setHighlighted] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    codeToHtml(data.snippet || "", {
      lang: data.language || "text",
      theme: "github-dark",
    })
      .then((html) => { if (!cancelled) setHighlighted(html); })
      .catch(() => { if (!cancelled) setHighlighted(""); });
    return () => { cancelled = true; };
  }, [data.snippet, data.language]);

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.filePath}>{data.file_path}</span>
        <span className={styles.lang}>{data.language}</span>
      </div>

      <div className={styles.codeBlock}>
        {highlighted ? (
          <div dangerouslySetInnerHTML={{ __html: highlighted }} className={styles.shiki} />
        ) : (
          <pre className={styles.fallback}><code>{data.snippet}</code></pre>
        )}
      </div>

      {data.insight && (
        <div className={styles.insight}>
          <span className={styles.insightLabel}>Insight</span>
          <p className={styles.insightText}>{data.insight}</p>
        </div>
      )}
    </div>
  );
}
