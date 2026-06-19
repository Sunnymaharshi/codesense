import { Sparkles } from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import styles from "./AskAIButton.module.css";

export function AskAIButton() {
  const { toggleChat, isOpen } = useChatStore();
  return (
    <button
      className={`${styles.btn} ${isOpen ? styles.btnActive : ""}`}
      onClick={toggleChat}
      aria-label="Ask AI about this developer"
    >
      <Sparkles size={16} />
      Ask AI
    </button>
  );
}
