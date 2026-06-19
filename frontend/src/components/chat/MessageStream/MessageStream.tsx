import { Suspense } from "react";
import { motion } from "framer-motion";
import type { ChatMessage } from "@/store/chatStore";
import { ThinkingSteps } from "@/components/chat/ThinkingSteps";
import { REGISTRY, type RegistryKey } from "@/lib/registry";
import { Skeleton } from "@/components/ui/Skeleton";
import styles from "./MessageStream.module.css";

interface MessageStreamProps {
  message: ChatMessage;
}

export function MessageStream({ message }: MessageStreamProps) {
  if (message.role === "user") {
    return (
      <div className={styles.userBubble}>
        <p className={styles.userText}>{message.rawText}</p>
      </div>
    );
  }

  const { thinkingSteps, isStreaming, component, rawText, error } = message;

  // Show error
  if (error) {
    return (
      <div className={styles.errorBubble}>
        <p className={styles.errorText}>{error}</p>
      </div>
    );
  }

  // Resolve component from registry
  const ComponentToRender = component?.type
    ? REGISTRY[component.type as RegistryKey] ?? null
    : null;

  return (
    <motion.div
      className={styles.assistantBubble}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Thinking steps */}
      <ThinkingSteps steps={thinkingSteps} isStreaming={isStreaming} />

      {/* Streaming text with cursor */}
      {rawText && !component && (
        <p className={styles.streamingText}>
          {rawText}
          {isStreaming && <span className={styles.cursor} aria-hidden />}
        </p>
      )}

      {/* Rendered AI component */}
      {component && ComponentToRender && (
        <Suspense fallback={<Skeleton height={120} width="100%" />}>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <ComponentToRender data={component.data} />
            {component.text && (
              <p className={styles.componentNarrative}>{component.text}</p>
            )}
          </motion.div>
        </Suspense>
      )}

      {/* Skeleton while waiting for first token */}
      {isStreaming && !rawText && thinkingSteps.length === 0 && (
        <div className={styles.skeletonWrap}>
          <Skeleton width="80%" height={14} />
          <Skeleton width="60%" height={14} />
        </div>
      )}
    </motion.div>
  );
}
