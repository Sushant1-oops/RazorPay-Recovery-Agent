import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowUpRight, Activity, ShieldAlert, CheckCircle2, Clock } from "lucide-react";
import { api, type Recovery } from "@/lib/api";
import { AppLayout, EmptyState, ErrorState } from "@/components/AppLayout";
import { StatusBadge } from "@/components/StatusBadge";
import { formatAmount, formatDuration, formatPercent, formatDateTime, titleCase } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Recovery Agent Ops — Payment Failure Dashboard" },
      {
        name: "description",
        content:
          "Track failed payments, recovery rate and revenue recovered by the AI payment failure recovery agent.",
      },
      { property: "og:title", content: "Recovery Agent Ops — Payment Failure Dashboard" },
      {
        property: "og:description",
        content: "Failed payments, recovery rate and recovered revenue at a glance.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Dashboard,
});

const CHART_COLORS = [
  "#2563eb",
  "#0ea5e9",
  "#6366f1",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
];

function Metric({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: React.ElementType;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 transition-shadow hover:shadow-xs">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
        {Icon ? <Icon className="size-4 text-muted-foreground/70" /> : null}
      </div>
      <p className="num mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function MiniConfidence({ value }: { value: number | null }) {
  if (value == null) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  const normalized = value > 1 ? Math.round(value) : Math.round(value * 100);
  const pct = Math.min(100, Math.max(0, normalized));

  const barColor =
    pct >= 75
      ? "bg-emerald-500"
      : pct >= 50
        ? "bg-blue-500"
        : pct >= 35
          ? "bg-amber-500"
          : "bg-rose-500";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="num text-xs font-medium text-muted-foreground">{pct}%</span>
    </div>
  );
}

function Dashboard() {
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: () => api.overview(),
    retry: false,
  });

  const breakdown = useQuery({
    queryKey: ["failure-breakdown"],
    queryFn: () => api.failureBreakdown(),
    retry: false,
  });

  const strategies = useQuery({
    queryKey: ["recovery-strategies"],
    queryFn: () => api.recoveryStrategies(),
    retry: false,
  });

  const recoveriesQuery = useQuery({
    queryKey: ["dashboard-recoveries"],
    queryFn: () => api.recoveries(),
    retry: false,
  });

  const o = overview.data;
  const recentRecoveries: Recovery[] = recoveriesQuery.data?.recoveries?.slice(0, 5) ?? [];

  return (
    <AppLayout title="Dashboard" subtitle="Recovery performance and AI agent operations across all ingested payments">
      {/* Metric Cards */}
      {overview.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
      ) : overview.error ? (
        <ErrorState message={(overview.error as Error).message} />
      ) : o ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric
            label="Total payments"
            value={String(o.total_payments)}
            hint={`${o.successful_payments} initial clean success`}
            icon={Activity}
          />
          <Metric
            label="Failed payments"
            value={String(o.failed_payments)}
            hint={`${o.recoverable_payments} actively in recovery pipeline`}
            icon={ShieldAlert}
          />
          <Metric
            label="Recovery rate"
            value={formatPercent(o.recovery_rate, true)}
            hint={`${o.recovered_payments} successfully recovered`}
            icon={CheckCircle2}
          />
          <Metric
            label="Recovered revenue"
            value={formatAmount(o.total_recovered_revenue)}
            hint={o.average_recovery_time_seconds > 0 ? `avg ${formatDuration(o.average_recovery_time_seconds)} to recover` : "waiting for next recovery"}
            icon={Clock}
          />
        </div>
      ) : null}

      {/* Charts & Strategies */}
      <div className="mt-6 grid gap-4 lg:grid-cols-5">
        <section className="rounded-lg border border-border bg-card p-5 lg:col-span-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Failure root causes</h2>
              <p className="text-xs text-muted-foreground">AI-classified root causes & error codes across failed payments</p>
            </div>
            {breakdown.data?.breakdown?.length ? (
              <span className="text-xs text-muted-foreground">
                {breakdown.data.breakdown.reduce((acc, b) => acc + b.count, 0)} total failures
              </span>
            ) : null}
          </div>

          <div className="mt-4 h-72">
            {breakdown.isLoading ? (
              <Skeleton className="h-full w-full rounded-md" />
            ) : breakdown.error ? (
              <ErrorState message={(breakdown.error as Error).message} />
            ) : !breakdown.data || breakdown.data.breakdown.length === 0 ? (
              <EmptyState
                title="No failures recorded"
                description="Failure types appear here once payment webhooks arrive."
              />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={breakdown.data.breakdown.map((b) => ({
                    ...b,
                    name: titleCase(b.failure_type),
                  }))}
                  margin={{ left: -10, right: 16, top: 12, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    interval={0}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: "var(--color-muted)", opacity: 0.5 }}
                    contentStyle={{
                      borderRadius: 8,
                      border: "1px solid var(--color-border)",
                      background: "var(--color-card)",
                      fontSize: 12,
                      boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                    }}
                    formatter={(value: number, _n, item) => [
                      `${value} payment${value !== 1 ? "s" : ""} (${(item.payload as { percentage: number }).percentage.toFixed(1)}%)`,
                      "Impact",
                    ]}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={48}>
                    {breakdown.data.breakdown.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Recovery strategies</h2>
              <p className="text-xs text-muted-foreground">Autonomous playbook execution & success rates</p>
            </div>
          </div>

          <div className="mt-4">
            {strategies.isLoading ? (
              <Skeleton className="h-40 w-full rounded-md" />
            ) : strategies.error ? (
              <ErrorState message={(strategies.error as Error).message} />
            ) : !strategies.data || strategies.data.strategies.length === 0 ? (
              <EmptyState
                title="No strategies run yet"
                description="Strategy performance builds up as the agent works recoveries."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs tracking-wide text-muted-foreground uppercase">
                      <th className="py-2 font-medium">Strategy</th>
                      <th className="py-2 text-center font-medium">Used</th>
                      <th className="py-2 text-right font-medium">Success</th>
                    </tr>
                  </thead>
                  <tbody>
                    {strategies.data.strategies.map((s) => (
                      <tr key={s.strategy} className="border-b border-border transition-colors last:border-0 hover:bg-surface/50">
                        <td className="py-2.5 font-medium">{titleCase(s.strategy)}</td>
                        <td className="num py-2.5 text-center text-muted-foreground">{s.count}</td>
                        <td className="num py-2.5 text-right font-medium">{formatPercent(s.success_rate, true)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Live Agent Recovery Feed */}
      <div className="mt-6 rounded-lg border border-border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-4">
          <div>
            <h2 className="text-sm font-semibold">Recent recovery runs</h2>
            <p className="text-xs text-muted-foreground">Live decisions, confidence ratings, and actions executed by the agent</p>
          </div>
          <Link
            to="/recoveries"
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            View all recoveries
            <ArrowUpRight className="size-3.5" />
          </Link>
        </div>

        <div className="mt-3">
          {recoveriesQuery.isLoading ? (
            <div className="space-y-2 py-4">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : recentRecoveries.length === 0 ? (
            <EmptyState
              title="No active recoveries"
              description="New failed payments will trigger the agent and appear here in real-time."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface/50 text-left text-xs tracking-wide text-muted-foreground uppercase">
                    <th className="px-4 py-3 font-medium">Payment</th>
                    <th className="px-4 py-3 font-medium">Root cause</th>
                    <th className="px-4 py-3 font-medium">AI confidence</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Strategy</th>
                    <th className="px-4 py-3 font-medium">Attempts</th>
                    <th className="px-4 py-3 text-right font-medium">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRecoveries.map((r) => (
                    <tr
                      key={r.id}
                      className="border-b border-border transition-colors last:border-0 hover:bg-surface/50"
                    >
                      <td className="num px-4 py-3 font-mono text-xs font-medium">
                        {r.payment?.razorpay_payment_id ?? `Payment #${r.payment_id}`}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status="neutral"
                          label={r.root_cause ? titleCase(r.root_cause) : "Analyzing..."}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <MiniConfidence value={r.root_cause_confidence} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {r.current_strategy ? titleCase(r.current_strategy) : "—"}
                      </td>
                      <td className="num px-4 py-3 text-xs text-muted-foreground">
                        {r.attempt_count} / {r.max_attempts}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                        {formatDateTime(r.updated_at || r.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
