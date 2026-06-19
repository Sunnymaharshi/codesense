import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send, Sparkles, Square } from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { useChat } from "@/hooks/useChat";
import { MessageStream } from "@/components/chat/MessageStream";
import styles from "./ChatPanel.module.css";

const SUGGESTIONS = [
  "When does this developer ship code?",
  "How strong are their backend skills?",
  "Summarise this developer's style",
  "Would you hire them for a startup?",
  "How have they grown over time?",
];

interface ChatPanelProps {
  username: string;
}

export function ChatPanel({ username }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const { messages, isStreaming, isOpen, closeChat } = useChatStore();
  const { sendMessage, abort } = useChat(username);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on new message
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

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className={styles.backdrop}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeChat}
          />

          {/* Panel */}
          <motion.div
            className={styles.panel}
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            {/* Header */}
            <div className={styles.header}>
              <div className={styles.headerTitle}>
                <Sparkles size={16} className={styles.sparkle} />
                <span>Ask about {username}</span>
              </div>
              <button className={styles.closeBtn} onClick={closeChat} aria-label="Close">
                <X size={18} />
              </button>
            </div>

            {/* Messages */}
            <div className={styles.messages}>
              {messages.length === 0 && (
                <div className={styles.empty}>
                  <p className={styles.emptyTitle}>Ask anything about this developer</p>
                  <div className={styles.suggestions}>
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        className={styles.suggestion}
                        onClick={() => { setInput(s); inputRef.current?.focus(); }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div key={msg.id} className={styles.messageWrap}>
                  <MessageStream message={msg} />
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className={styles.inputArea}>
              <textarea
                ref={inputRef}
                className={styles.input}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about commit patterns, skills, code quality…"
                rows={2}
                disabled={isStreaming}
              />
              <button
                className={styles.sendBtn}
                onClick={isStreaming ? abort : handleSend}
                aria-label={isStreaming ? "Stop" : "Send"}
              >
                {isStreaming ? <Square size={16} /> : <Send size={16} />}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
