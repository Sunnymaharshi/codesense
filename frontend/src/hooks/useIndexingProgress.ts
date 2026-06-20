/**
 * useIndexingProgress
 *
 * Opens a WebSocket to /ws/{username} while indexStatus is "pending" or "running".
 * Drives reposDone / reposTotal / indexStatus / agentStatus in the Zustand store.
 *
 * Lifecycle:
 *   indexing "done"  → WS stays open, agent events follow
 *   "agent_done"     → refetch profile (skill_scores now populated), WS closes
 *   90s timeout      → safety close if no agent events arrive after indexing done
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
  onAgentDone?: () => void;
}

export function useIndexingProgress(
  username: string | null,
  { onDone, onAgentDone }: Options = {},
) {
  const { indexStatus, wsSession, setIndexStatus, setProgress, setError, setAgentStatus } =
    useProfileStore();
  const wsRef = useRef<WebSocket | null>(null);
  const onDoneRef = useRef(onDone);
  const onAgentDoneRef = useRef(onAgentDone);
  const agentTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  onDoneRef.current = onDone;
  onAgentDoneRef.current = onAgentDone;

  useEffect(() => {
    if (!username) return;
    if (indexStatus === "done") return;
    if (indexStatus === "error") return;

    let rafId: number;
    let ws: WebSocket | null = null;

    const closeWs = () => {
      if (agentTimeoutRef.current) {
        clearTimeout(agentTimeoutRef.current);
        agentTimeoutRef.current = null;
      }
      ws?.close();
    };

    rafId = requestAnimationFrame(() => {
      const url = `${WS_BASE}/ws/${encodeURIComponent(username)}`;
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Don't set status here — wait for actual server messages.
        // Setting "running" on open caused a false loading banner on every page refresh.
      };

      ws.onmessage = (event: MessageEvent<string>) => {
        let msg: WsProgressMessage;
        try {
          msg = JSON.parse(event.data);
        } catch {
          return;
        }

        switch (msg.type) {
          case "started":
            setIndexStatus("running");
            setProgress(msg.repos_done ?? 0, msg.repos_total ?? 0);
            break;

          case "progress":
            setIndexStatus("running");
            setProgress(msg.repos_done ?? 0, msg.repos_total ?? 0);
            break;

          case "done":
            setProgress(msg.repos_done ?? 0, msg.repos_total ?? 0);
            setIndexStatus("done");
            onDoneRef.current?.();
            // Keep WS open for agent events — safety close after 90s
            agentTimeoutRef.current = setTimeout(closeWs, 90_000);
            break;

          case "agent_started":
            setAgentStatus("running", null);
            break;

          case "agent_step":
            setAgentStatus("running", msg.step ?? null);
            break;

          case "agent_done":
            setAgentStatus("done");
            closeWs();
            onAgentDoneRef.current?.();
            break;

          case "agent_error":
            setAgentStatus("error");
            closeWs();
            break;

          case "error":
            setIndexStatus("error");
            setError(msg.message ?? "Indexing failed");
            closeWs();
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
      closeWs();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username, wsSession]);
}
