/**
 * useChat — SSE streaming hook for the RAG query endpoint.
 *
 * Parses the SSE event protocol:
 *   thinking_step → drives ThinkingSteps UI
 *   token         → appends chars one by one (typing effect)
 *   component     → sets parsed AIMessage on the message
 *   done          → marks streaming complete
 *   error         → sets error state
 */
import { useRef } from "react";
import { useChatStore } from "@/store/chatStore";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export function useChat(username: string) {
  const abortRef = useRef<AbortController | null>(null);
  const {
    addUserMessage,
    addAssistantMessage,
    appendToken,
    addThinkingStep,
    updateThinkingStep,
    setComponent,
    setStreamingDone,
    setError,
    setIsStreaming,
  } = useChatStore();

  async function sendMessage(question: string) {
    if (!question.trim()) return;

    // Abort any in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    addUserMessage(question);
    const assistantId = addAssistantMessage();
    setIsStreaming(true);

    try {
      const response = await fetch(`${API_BASE}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, question }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Request failed" }));
        setError(assistantId, err.detail ?? "Request failed");
        setIsStreaming(false);
        return;
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6).trim();
            if (!raw) continue;

            let payload: Record<string, unknown>;
            try {
              payload = JSON.parse(raw);
            } catch {
              continue;
            }

            switch (currentEvent) {
              case "thinking_step": {
                const msg = payload.message as string;
                const isDone = payload.done as boolean;
                if (!isDone) {
                  addThinkingStep(assistantId, { message: msg, done: false });
                } else {
                  updateThinkingStep(assistantId, msg, true);
                }
                break;
              }
              case "token":
                appendToken(assistantId, payload.char as string);
                break;
              case "component":
                setComponent(assistantId, payload as any);
                break;
              case "done":
                setStreamingDone(assistantId);
                setIsStreaming(false);
                break;
              case "error":
                setError(assistantId, payload.message as string ?? "Unknown error");
                setIsStreaming(false);
                break;
            }
            currentEvent = "";
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(assistantId, err instanceof Error ? err.message : "Stream failed");
      setIsStreaming(false);
    }
  }

  function abort() {
    abortRef.current?.abort();
    setIsStreaming(false);
  }

  return { sendMessage, abort };
}
