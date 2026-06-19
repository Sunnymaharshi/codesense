/**
 * Phase 2 profile store — adds "idle" status + error field
 * compared to Phase 1 version.
 */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

export type IndexStatus = "idle" | "pending" | "running" | "done" | "error";

interface ProfileState {
  username: string | null;
  indexStatus: IndexStatus;
  reposDone: number;
  reposTotal: number;
  jobId: string | null;
  error: string | null;
}

interface ProfileActions {
  setUsername: (username: string) => void;
  setIndexStatus: (status: IndexStatus) => void;
  setProgress: (done: number, total: number) => void;
  setJobId: (jobId: string) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState: ProfileState = {
  username: null,
  indexStatus: "idle",
  reposDone: 0,
  reposTotal: 0,
  jobId: null,
  error: null,
};

export const useProfileStore = create<ProfileState & ProfileActions>()(
  immer((set) => ({
    ...initialState,

    setUsername: (username) =>
      set((s) => { s.username = username; }),

    setIndexStatus: (status) =>
      set((s) => { s.indexStatus = status; }),

    setProgress: (done, total) =>
      set((s) => { s.reposDone = done; s.reposTotal = total; }),

    setJobId: (jobId) =>
      set((s) => { s.jobId = jobId; }),

    setError: (error) =>
      set((s) => { s.error = error; }),

    reset: () => set((s) => { Object.assign(s, initialState); }),
  })),
);
