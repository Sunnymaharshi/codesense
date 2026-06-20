/**
 * Phase 2 profile store — adds "idle" status + error field
 * compared to Phase 1 version.
 */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

export type IndexStatus = "idle" | "pending" | "running" | "done" | "error";
export type AgentStatus = "idle" | "running" | "done" | "error";

interface ProfileState {
  username: string | null;
  indexStatus: IndexStatus;
  reposDone: number;
  reposTotal: number;
  jobId: string | null;
  error: string | null;
  agentStatus: AgentStatus;
  agentStep: string | null;
  wsSession: number;
}

interface ProfileActions {
  setUsername: (username: string) => void;
  setIndexStatus: (status: IndexStatus) => void;
  setProgress: (done: number, total: number) => void;
  setJobId: (jobId: string | null) => void;
  setError: (error: string | null) => void;
  setAgentStatus: (status: AgentStatus, step?: string | null) => void;
  incrementWsSession: () => void;
  reset: () => void;
}

const initialState: ProfileState = {
  username: null,
  indexStatus: "idle",
  reposDone: 0,
  reposTotal: 0,
  jobId: null,
  error: null,
  agentStatus: "idle",
  agentStep: null,
  wsSession: 0,
};

export const useProfileStore = create<ProfileState & ProfileActions>()(
  immer((set) => ({
    ...initialState,

    setUsername: (username) =>
      set((s) => {
        if (s.username !== username) {
          s.indexStatus = "idle";
          s.reposDone = 0;
          s.reposTotal = 0;
          s.agentStatus = "idle";
          s.agentStep = null;
          s.error = null;
          s.wsSession += 1;  // increment (not reset) so the effect dep always changes
        }
        s.username = username;
      }),

    setIndexStatus: (status) =>
      set((s) => { s.indexStatus = status; }),

    setProgress: (done, total) =>
      set((s) => { s.reposDone = done; s.reposTotal = total; }),

    setJobId: (jobId) =>
      set((s) => { s.jobId = jobId; }),

    setError: (error) =>
      set((s) => { s.error = error; }),

    setAgentStatus: (status, step = null) =>
      set((s) => { s.agentStatus = status; s.agentStep = step ?? null; }),

    incrementWsSession: () =>
      set((s) => { s.wsSession += 1; }),

    reset: () => set((s) => { Object.assign(s, initialState); }),
  })),
);
