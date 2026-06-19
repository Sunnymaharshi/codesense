import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { IndexStatus } from "@/lib/types";

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
  indexStatus: "idle" as IndexStatus,
  reposDone: 0,
  reposTotal: 0,
  jobId: null,
  error: null,
};

export const useProfileStore = create<ProfileState & ProfileActions>()(
  immer((set) => ({
    ...initialState,

    setUsername: (username) =>
      set((state) => {
        state.username = username;
      }),

    setIndexStatus: (status) =>
      set((state) => {
        state.indexStatus = status;
      }),

    setProgress: (done, total) =>
      set((state) => {
        state.reposDone = done;
        state.reposTotal = total;
      }),

    setJobId: (jobId) =>
      set((state) => {
        state.jobId = jobId;
      }),

    setError: (error) =>
      set((state) => {
        state.error = error;
      }),

    reset: () =>
      set((state) => {
        Object.assign(state, initialState);
      }),
  })),
);
