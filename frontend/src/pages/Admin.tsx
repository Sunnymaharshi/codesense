import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, DollarSign, Zap, Clock, Activity } from "lucide-react";
import styles from "./Admin.module.css";

interface AdminStats {
  total_calls: number;
  total_cost_usd: number;
  avg_duration_ms: number;
  calls_last_24h: number;
  tokens_in_total: number;
  tokens_out_total: number;
}

interface CallRow {
  id: number;
  endpoint: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  duration_ms: number;
  github_username: string | null;
  created_at: string;
}

async function fetchStats(): Promise<AdminStats> {
  const res = await fetch("/api/admin/stats");
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

async function fetchCalls(): Promise<{ calls: CallRow[] }> {
  const res = await fetch("/api/admin/calls");
  if (!res.ok) throw new Error("Failed to fetch calls");
  return res.json();
}

export function Admin() {
  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: fetchStats,
    refetchInterval: 30_000,
  });

  const { data: callsData, refetch: refetchCalls } = useQuery({
    queryKey: ["admin-calls"],
    queryFn: fetchCalls,
    refetchInterval: 30_000,
  });

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.backLink}>
          <ArrowLeft size={16} />
          codesense
        </Link>
        <span className={styles.title}>Admin</span>
      </nav>

      <div className={styles.container}>
        <div className={styles.statsGrid}>
          <StatCard
            icon={<Activity size={18} />}
            label="Total calls"
            value={stats?.total_calls ?? "—"}
          />
          <StatCard
            icon={<DollarSign size={18} />}
            label="Total cost"
            value={stats ? `$${stats.total_cost_usd.toFixed(4)}` : "—"}
          />
          <StatCard
            icon={<Clock size={18} />}
            label="Avg latency"
            value={stats ? `${Math.round(stats.avg_duration_ms)}ms` : "—"}
          />
          <StatCard
            icon={<Zap size={18} />}
            label="Last 24h"
            value={stats?.calls_last_24h ?? "—"}
          />
        </div>

        {stats && (
          <div className={styles.tokenRow}>
            <span className={styles.tokenStat}>
              {stats.tokens_in_total.toLocaleString()} tokens in
            </span>
            <span className={styles.tokenDivider}>·</span>
            <span className={styles.tokenStat}>
              {stats.tokens_out_total.toLocaleString()} tokens out
            </span>
          </div>
        )}

        <table className={styles.table}>
          <thead>
            <tr>
              <th>Time</th>
              <th>Endpoint</th>
              <th>Model</th>
              <th>User</th>
              <th>Tokens in</th>
              <th>Tokens out</th>
              <th>Cost</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody>
            {callsData?.calls.map((call) => (
              <tr key={call.id}>
                <td className={styles.mono}>
                  {new Date(call.created_at).toLocaleTimeString()}
                </td>
                <td className={styles.mono}>{call.endpoint}</td>
                <td className={styles.mono}>{call.model.split("-")[0]}</td>
                <td className={styles.mono}>{call.github_username ?? "—"}</td>
                <td className={styles.mono}>{call.tokens_in.toLocaleString()}</td>
                <td className={styles.mono}>{call.tokens_out.toLocaleString()}</td>
                <td className={styles.mono}>${call.cost_usd.toFixed(5)}</td>
                <td className={styles.mono}>{call.duration_ms}ms</td>
              </tr>
            ))}
            {!callsData?.calls.length && (
              <tr>
                <td colSpan={8} className={styles.empty}>No calls logged yet</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className={styles.statCard}>
      <div className={styles.statIcon}>{icon}</div>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  );
}
