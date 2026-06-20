/**
 * useIndexingProgress
 *
 * Opens a WebSocket to /ws/{username} while indexStatus is "pending" or "running".
 * Drives reposDone / reposTotal / indexStatus in the Zustand store.
 * Calls onDone() when the server fires "done" — Profile page uses this to refetch.
 */

import { useEffect, useRef } from "react";
import { useProfileStore } from "@/store/profileStore";
import type { WsProgressMessage } from "@/lib/types";

const WS_BASE =
  import.meta.env.VITE_WS_URL ??
  (window.location.protocol === "https:" ? "wss://" : "ws://") +
    window.location.host;

interface Options {
  onDone?: () => void;
}

export function useIndexingProgress(
  username: string | null,
  { onDone }: Options = {},
) {
  const { indexStatus, setIndexStatus, setProgress, setError } =
    useProfileStore();
  const wsRef = useRef<WebSocket | null>(null);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!username) return;
    if (indexStatus === "done") return;   // already finished — don't reconnect
    if (indexStatus === "error") return;

    let rafId: number;
    let ws: WebSocket | null = null;

    // Defer until after first paint so the profile skeleton renders immediately
    rafId = requestAnimationFrame(() => {
      const url = `${WS_BASE}/ws/${encodeURIComponent(username)}`;
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIndexStatus("running");
      };

      ws.onmessage = (event: MessageEvent<string>) => {
        let msg: WsProgressMessage;
        try {
          msg = JSON.parse(event.data);
        } catch {
          return;
        }

        switch (msg.type) {
          case "progress":
            setProgress(msg.repos_done, msg.repos_total);
            break;
          case "done":
            setProgress(msg.repos_done, msg.repos_total);
            setIndexStatus("done");
            ws?.close();
            onDoneRef.current?.();
            break;
          case "error":
            setIndexStatus("error");
            setError(msg.message ?? "Indexing failed");
            ws?.close();
            break;
        }
      };

      ws.onerror = () => {
        setIndexStatus("error");
        setError("WebSocket connection failed");
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    });

    return () => {
      cancelAnimationFrame(rafId);
      ws?.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username]);
}
