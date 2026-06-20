import { useState, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Search, ArrowRight, AlertCircle } from "lucide-react";
import { analyzeUser } from "@/lib/api";
import { useProfileStore } from "@/store/profileStore";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import styles from "./Home.module.css";

const EXAMPLES = ["sunnymaharshi", "torvalds", "gvanrossum", "antirez", "sindresorhus"];

export function Home() {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { setUsername, setJobId, setIndexStatus } = useProfileStore();

  async function handleSubmit(username: string) {
    const clean = username.trim().replace(/^@/, "").toLowerCase();
    if (!clean) return;

    setLoading(true);
    setError(null);

    try {
      const res = await analyzeUser(clean);
      setUsername(clean);
      setJobId(res.job_id);
      setIndexStatus(res.status);
      // navigate is synchronous in TanStack Router — no await needed,
      // but setLoading(false) must be called so the spinner clears if
      // Profile ever unmounts back to Home (error boundary etc.)
      setLoading(false);
      navigate({ to: "/u/$username", params: { username: clean } });
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.name === "AbortError"
            ? "Request timed out — is the backend running?"
            : err.message
          : "Something went wrong";
      setError(msg);
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit(input);
  }

  return (
    <main className={styles.main}>
      <div className={styles.topRight}>
        <ThemeToggle />
      </div>
      <motion.div
        className={styles.center}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {/* Logo */}
        <div className={styles.logo}>
          <span className={styles.logoText}>codesense</span>
          <span className={styles.logoBadge}>AI-powered</span>
        </div>

        <p className={styles.tagline}>The complete picture of any GitHub developer.</p>

        {/* Search input */}
        <div className={styles.inputWrap}>
          <Search size={18} className={styles.inputIcon} />
          <input
            ref={inputRef}
            className={styles.input}
            type="text"
            placeholder="GitHub username"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            autoFocus
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            disabled={loading}
          />
          <button
            className={styles.submitBtn}
            onClick={() => handleSubmit(input)}
            disabled={loading || !input.trim()}
            aria-label="Analyze developer"
          >
            {loading ? (
              <span className={styles.spinner} aria-hidden />
            ) : (
              <ArrowRight size={18} />
            )}
          </button>
        </div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              className={styles.error}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <AlertCircle size={14} />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Example links */}
        <div className={styles.examples}>
          <span className={styles.examplesLabel}>Try:</span>
          {EXAMPLES.map((name) => (
            <button
              key={name}
              className={styles.exampleBtn}
              onClick={() => handleSubmit(name)}
              disabled={loading}
            >
              {name}
            </button>
          ))}
        </div>
      </motion.div>
    </main>
  );
}
