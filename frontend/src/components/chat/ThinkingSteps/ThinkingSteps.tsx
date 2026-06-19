import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import type { ThinkingStep } from "@/store/chatStore";
import styles from "./ThinkingSteps.module.css";

interface ThinkingStepsProps {
  steps: ThinkingStep[];
  isStreaming: boolean;
}

export function ThinkingSteps({ steps, isStreaming }: ThinkingStepsProps) {
  if (steps.length === 0) return null;

  return (
    <div className={styles.container}>
      <AnimatePresence initial={false}>
        {steps.map((step, i) => (
          <motion.div
            key={`${step.message}-${i}`}
            className={styles.step}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
          >
            <span className={styles.icon}>
              {step.done ? (
                <Check size={12} className={styles.iconDone} />
              ) : (
                <Loader2 size={12} className={styles.iconPending} />
              )}
            </span>
            <span className={`${styles.text} ${step.done ? styles.textDone : styles.textPending}`}>
              {step.message}
            </span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
