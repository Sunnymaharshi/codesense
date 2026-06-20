import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

export interface ThinkingStep {
  message: string;
  done: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  // For assistant messages — built up token by token
  rawText: string;
  // Parsed component — set when "component" event arrives
  component: { type: string; text: string; data: Record<string, unknown> } | null;
  isStreaming: boolean;
  thinkingSteps: ThinkingStep[];
  error: string | null;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  isOpen: boolean;
}

interface ChatActions {
  openChat: () => void;
  closeChat: () => void;
  toggleChat: () => void;
  addUserMessage: (text: string) => string;
  addAssistantMessage: () => string;
  appendToken: (id: string, char: string) => void;
  addThinkingStep: (id: string, step: ThinkingStep) => void;
  updateThinkingStep: (id: string, message: string, done: boolean) => void;
  setComponent: (id: string, component: ChatMessage["component"]) => void;
  setStreamingDone: (id: string) => void;
  setError: (id: string, error: string) => void;
  setIsStreaming: (v: boolean) => void;
  clear: () => void;
}

let msgCounter = 0;
const nextId = () => `msg_${++msgCounter}_${Date.now()}`;

export const useChatStore = create<ChatState & ChatActions>()(
  immer((set) => ({
    messages: [],
    isStreaming: false,
    isOpen: false,

    openChat: () => set((s) => { s.isOpen = true; }),
    closeChat: () => set((s) => { s.isOpen = false; }),
    toggleChat: () => set((s) => { s.isOpen = !s.isOpen; }),

    addUserMessage: (text) => {
      const id = nextId();
      set((s) => {
        s.messages.push({
          id, role: "user", rawText: text,
          component: null, isStreaming: false,
          thinkingSteps: [], error: null,
        });
      });
      return id;
    },

    addAssistantMessage: () => {
      const id = nextId();
      set((s) => {
        s.messages.push({
          id, role: "assistant", rawText: "",
          component: null, isStreaming: true,
          thinkingSteps: [], error: null,
        });
      });
      return id;
    },

    appendToken: (id, char) => set((s) => {
      const msg = s.messages.find((m) => m.id === id);
      if (msg) msg.rawText += char;
    }),

    addThinkingStep: (id, step) => set((s) => {
      const msg = s.messages.find((m) => m.id === id);
      if (msg) msg.thinkingSteps.push(step);
    }),

    updateThinkingStep: (id, message, done) => set((s) => {
      const msg = s.messages.find((m) => m.id === id);
      if (!msg) return;
      // Find last pending step and update its text + done flag.
      // The completion message may differ from the start message (e.g. "Searching…" → "Found 8 chunks").
      const step = [...msg.thinkingSteps].reverse().find((st) => !st.done);
      if (step) { step.message = message; step.done = done; }
    }),

    setComponent: (id, component) => set((s) => {
      const msg = s.messages.find((m) => m.id === id);
      if (msg) msg.component = component;
    }),

    setStreamingDone: (id) => set((s) => {
      const msg = s.messages.find((m) => m.id === id);
      if (msg) msg.isStreaming = false;
    }),

    setError: (id, error) => set((s) => {
      const msg = s.messages.find((m) => m.id === id);
      if (msg) { msg.error = error; msg.isStreaming = false; }
    }),

    setIsStreaming: (v) => set((s) => { s.isStreaming = v; }),

    clear: () => set((s) => { s.messages = []; }),
  })),
);
