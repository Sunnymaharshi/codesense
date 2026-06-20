import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, Square, Clock, Code2, TrendingUp, User } from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { useChat } from "@/hooks/useChat";
import { MessageStream } from "@/components/chat/MessageStream";
import styles from "./InlineChatPanel.module.css";

const SUGGESTIONS = [
  { icon: Clock,     text: "When does this developer ship code?" },
  { icon: Code2,     text: "How strong are their backend skills?" },
  { icon: User,      text: "Summarise their coding style" },
  { icon: TrendingUp, text: "How have they grown over time?" },
];

interface Props {
  username: string;
}

export function InlineChatPanel({ username }: Props) {
  const [input, setInput] = useState("");
  const { messages, isStreaming } = useChatStore();
  const { sendMessage, abort } = useChat(username);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isStreaming]);

  async function handleSend() {
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput("");
    await sendMessage(q);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleSuggestion(text: string) {
    setInput(text);
    inputRef.current?.focus();
  }

  const hasMessages = messages.length > 0;

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <Sparkles size={16} className={styles.headerIcon} />
        <div className={styles.headerText}>
          <span className={styles.headerTitle}>Ask AI</span>
          <span className={styles.headerSub}>about {username}</span>
        </div>
        {isStreaming && (
          <span className={styles.streamingDot} title="Thinking…" />
        )}
      </div>

      {/* Messages / Empty state */}
      <div className={styles.messages}>
        <AnimatePresence mode="popLayout">
          {!hasMessages && (
            <motion.div
              key="empty"
              className={styles.empty}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <p className={styles.emptyLabel}>Try asking</p>
              <div className={styles.suggestions}>
                {SUGGESTIONS.map(({ icon: Icon, text }) => (
                  <button
                    key={text}
                    className={styles.chip}
                    onClick={() => handleSuggestion(text)}
                  >
                    <Icon size={13} className={styles.chipIcon} />
                    {text}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              className={styles.messageWrap}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <MessageStream message={msg} />
            </motion.div>
          ))}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className={styles.inputArea}>
        <div className={styles.inputWrap}>
          <textarea
            ref={inputRef}
            className={styles.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about skills, patterns, growth…"
            rows={2}
            disabled={isStreaming}
          />
          <button
            className={`${styles.sendBtn} ${isStreaming ? styles.sendBtnStop : ""}`}
            onClick={isStreaming ? abort : handleSend}
            aria-label={isStreaming ? "Stop" : "Send"}
            disabled={!isStreaming && !input.trim()}
          >
            {isStreaming ? <Square size={14} /> : <Send size={14} />}
          </button>
        </div>
      </div>
    </div>
  );
}
