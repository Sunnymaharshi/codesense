import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { GitCompare } from "lucide-react";
import styles from "./CompareEntry.module.css";

interface Props {
  username: string;
}

export function CompareEntry({ username }: Props) {
  const [other, setOther] = useState("");
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  function handleSubmit() {
    const clean = other.trim().replace(/^@/, "").toLowerCase();
    if (!clean) return;
    navigate({ to: "/compare/$user1/$user2", params: { user1: username, user2: clean } });
  }

  if (!open) {
    return (
      <button className={styles.trigger} onClick={() => setOpen(true)}>
        <GitCompare size={14} />
        Compare with…
      </button>
    );
  }

  return (
    <div className={styles.form}>
      <input
        className={styles.input}
        placeholder="other username"
        value={other}
        onChange={(e) => setOther(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        autoFocus
      />
      <button className={styles.go} onClick={handleSubmit}>Go</button>
    </div>
  );
}
