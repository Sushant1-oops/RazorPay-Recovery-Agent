import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pause, Play, Clock, CheckCircle2, XCircle, Loader2, AlertTriangle, ShieldCheck } from "lucide-react";
import { api, type Recovery, type RecoveryAction } from "@/lib/api";
import { AppLayout, EmptyState, ErrorState } from "@/components/AppLayout";
import { StatusBadge, statusTone } from "@/components/StatusBadge";
import { formatAmount, formatDateTime, titleCase } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";

export const Route = createFileRoute("/recoveries")({
  head: () => ({
    meta: [
      { title: "Recoveries — Recovery Agent Ops" },
      {
        name: "description",
        content:
          "Live view of every AI recovery run: root cause, recoverability score, strategy and the full action timeline.",
      },
      { property: "og:title", content: "Recoveries — Recovery Agent Ops" },
      {
        property: "og:description",
        content: "Root cause, recoverability score and agent action timeline per recovery.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: RecoveriesPage,
});

function Confidence({ value }: { value: number | null }) {
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
    <div className="flex min-w-28 items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="num text-xs font-medium text-muted-foreground">{pct}%</span>
    </div>
  );
}

function Gauge({ value }: { value: number | null }) {
  if (value == null) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs tracking-wide text-muted-foreground uppercase">
          Recoverability score
        </p>
        <p className="num mt-2 text-3xl font-semibold text-muted-foreground">—</p>
      </div>
    );
  }
  // Recoverability score from backend is already on a 0-100 scale
  const normalized = value > 1 || value === 0 ? Math.round(value) : Math.round(value * 100);
  const pct = Math.min(100, Math.max(0, normalized));
  const tone = pct >= 66 ? "text-success" : pct >= 33 ? "text-progress" : "text-danger";
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs tracking-wide text-muted-foreground uppercase">
        Recoverability score
      </p>
      <p className={`num mt-2 text-3xl font-semibold ${tone}`}>
        {pct}
        <span className="text-base text-muted-foreground">/100</span>
      </p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all ${pct >= 66 ? "bg-success" : pct >= 33 ? "bg-progress" : "bg-danger"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ActionIcon({ status }: { status: string }) {
  const tone = statusTone(status);
  if (tone === "success") return <CheckCircle2 className="size-4 text-success" />;
  if (tone === "danger") return <XCircle className="size-4 text-danger" />;
  if (tone === "progress") return <Loader2 className="size-4 text-progress" />;
  return <Clock className="size-4 text-muted-foreground" />;
}

function Timeline({ actions, recovery }: { actions: RecoveryAction[]; recovery?: Recovery }) {
  if (!actions || actions.length === 0) {
    if (recovery?.status === "recovered") {
      return (
        <ol className="relative space-y-5 border-l border-border pl-6">
          <li className="relative">
            <span className="absolute -left-[31px] flex size-5 items-center justify-center rounded-full bg-card ring-4 ring-card">
              <CheckCircle2 className="size-4 text-success" />
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">Payment Recovered</span>
              <StatusBadge status="recovered" />
              <span className="num text-xs text-muted-foreground">
                {formatDateTime(recovery.recovered_at)}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {recovery.explanation ?? "Payment successfully captured and recovered."}
            </p>
          </li>
        </ol>
      );
    }
    return (
      <p className="rounded-md border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
        The agent hasn't taken any action on this payment yet.
      </p>
    );
  }
  return (
    <ol className="relative space-y-5 border-l border-border pl-6">
      {actions.map((a, idx) => (
        <li key={a.id || idx} className="relative">
          <span className="absolute -left-[31px] flex size-5 items-center justify-center rounded-full bg-card ring-4 ring-card">
            <ActionIcon status={a.action_status} />
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{titleCase(a.action_type)}</span>
            <StatusBadge status={a.action_status} />
            <span className="num text-xs text-muted-foreground">
              {formatDateTime(a.started_at ?? a.completed_at)}
            </span>
          </div>
          {a.reason ? <p className="mt-1 text-sm text-muted-foreground">{a.reason}</p> : null}
          {a.parameters && Object.keys(a.parameters).length > 0 ? (
            <pre className="num mt-2 overflow-x-auto rounded-md bg-surface p-2 text-xs text-muted-foreground">
              {JSON.stringify(a.parameters, null, 2)}
            </pre>
          ) : null}
          {a.result && Object.keys(a.result).length > 0 ? (
            <pre className="num mt-2 overflow-x-auto rounded-md bg-surface p-2 text-xs text-muted-foreground">
              {JSON.stringify(a.result, null, 2)}
            </pre>
          ) : null}
        </li>
      ))}
      {recovery?.status === "recovered" ? (
        <li className="relative">
          <span className="absolute -left-[31px] flex size-5 items-center justify-center rounded-full bg-card ring-4 ring-card">
            <CheckCircle2 className="size-4 text-success" />
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">Payment Recovered Successfully</span>
            <StatusBadge status="recovered" />
            <span className="num text-xs text-muted-foreground">
              {formatDateTime(recovery.recovered_at)}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {recovery.explanation ?? "Payment successfully confirmed and captured. Recovery completed."}
          </p>
        </li>
      ) : null}
    </ol>
  );
}

function DetailSheet({
  recovery,
  onClose,
}: {
  recovery: Recovery | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const control = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "pause" | "resume" }) =>
      action === "pause" ? api.pauseRecovery(id) : api.resumeRecovery(id),
    onSuccess: (res) => {
      toast.success(res.message);
      void qc.invalidateQueries({ queryKey: ["recoveries"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const review = useMutation({
    mutationFn: ({
      id,
      decision,
      notes,
    }: {
      id: string;
      decision: "approve_retry" | "reject" | "resolve";
      notes?: string;
    }) => api.reviewRecovery(id, decision, notes),
    onSuccess: (res) => {
      toast.success(res.message);
      void qc.invalidateQueries({ queryKey: ["recoveries"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <Sheet open={!!recovery} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        {recovery ? (
          <>
            <SheetHeader>
              <SheetTitle className="flex flex-wrap items-center gap-2">
                <span className="num text-sm">
                  {recovery.payment?.razorpay_payment_id ?? recovery.payment_id}
                </span>
                <StatusBadge
                  status={recovery.status}
                  label={recovery.status === "escalated" ? "Review Required" : undefined}
                />
              </SheetTitle>
              <SheetDescription>
                Opened {formatDateTime(recovery.created_at)} · attempt {recovery.attempt_count} of{" "}
                {recovery.max_attempts}
              </SheetDescription>
            </SheetHeader>

            <div className="space-y-6 px-4 pb-8">
              {recovery.status === "escalated" ? (
                <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 shadow-sm space-y-3">
                  <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                    <AlertTriangle className="size-4 animate-pulse text-amber-400" />
                    <span>⚠️ HUMAN REVIEW REQUIRED</span>
                  </div>

                  <div className="space-y-1 text-xs">
                    <p className="text-muted-foreground font-medium uppercase tracking-wider text-[10px]">
                      Reason for Escalation
                    </p>
                    <p className="text-foreground text-sm font-medium">
                      {recovery.explanation?.replace(/^⚠️ Human Review Required:\s*/, "") ??
                        "High risk flag or ambiguous failure code requires human operator review."}
                    </p>
                  </div>

                  <div className="rounded-md bg-card/75 p-3 border border-border text-xs text-muted-foreground space-y-1">
                    <p className="font-semibold text-foreground">AI Policy Guardrail:</p>
                    <p>
                      Automated retries have been paused to protect customer experience and merchant limits.
                      Review failure details and approve retry, reject, or mark resolved.
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button
                      size="sm"
                      className="bg-amber-600 hover:bg-amber-700 text-white gap-1.5 text-xs font-medium"
                      disabled={review.isPending}
                      onClick={() =>
                        review.mutate({
                          id: recovery.id,
                          decision: "approve_retry",
                          notes: "Operator approved retry after reviewing failure evidence.",
                        })
                      }
                    >
                      <CheckCircle2 className="size-3.5" />
                      Approve Retry
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      className="border-red-500/30 text-red-400 hover:bg-red-500/10 gap-1.5 text-xs font-medium"
                      disabled={review.isPending}
                      onClick={() =>
                        review.mutate({
                          id: recovery.id,
                          decision: "reject",
                          notes: "Operator rejected recovery run.",
                        })
                      }
                    >
                      <XCircle className="size-3.5" />
                      Reject & Stop
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      className="border-green-500/30 text-green-400 hover:bg-green-500/10 gap-1.5 text-xs font-medium"
                      disabled={review.isPending}
                      onClick={() =>
                        review.mutate({
                          id: recovery.id,
                          decision: "resolve",
                          notes: "Operator confirmed payment resolved offline/manually.",
                        })
                      }
                    >
                      <ShieldCheck className="size-3.5" />
                      Mark Resolved
                    </Button>
                  </div>
                </div>
              ) : null}

              <div className="rounded-lg border border-accent/25 bg-accent/5 p-4">
                <p className="text-xs tracking-wide text-muted-foreground uppercase">
                  Agent reasoning
                </p>
                <p className="mt-2 text-sm leading-relaxed">
                  {recovery.explanation ?? "No explanation recorded yet."}
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Gauge value={recovery.recoverability_score} />
                <div className="rounded-lg border border-border bg-card p-4">
                  <p className="text-xs tracking-wide text-muted-foreground uppercase">
                    Root cause
                  </p>
                  <div className="mt-2">
                    <StatusBadge status="neutral" label={titleCase(recovery.root_cause)} />
                  </div>
                  <p className="mt-3 text-xs text-muted-foreground">Confidence</p>
                  <div className="mt-1">
                    <Confidence value={recovery.root_cause_confidence} />
                  </div>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Current strategy" value={titleCase(recovery.current_strategy)} />
                <Field label="Current step" value={titleCase(recovery.current_step)} />
                <Field label="Next action" value={titleCase(recovery.next_action)} />
                <Field label="Next action at" value={formatDateTime(recovery.next_action_at)} />
                <Field label="Recovered at" value={formatDateTime(recovery.recovered_at)} />
                <Field label="Last update" value={formatDateTime(recovery.updated_at)} />
              </div>

              {recovery.payment ? (
                <div className="rounded-lg border border-border bg-card p-4">
                  <p className="text-xs tracking-wide text-muted-foreground uppercase">
                    Payment failure
                  </p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <Field
                      label="Amount"
                      value={formatAmount(recovery.payment.amount, recovery.payment.currency)}
                    />
                    <Field label="Method" value={titleCase(recovery.payment.payment_method)} />
                    <Field label="Failure code" value={recovery.payment.failure_code ?? "—"} />
                    <Field label="Status" value={titleCase(recovery.payment.status)} />
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">
                    {recovery.payment.failure_reason ?? "No failure reason reported."}
                  </p>
                </div>
              ) : null}

              <div>
                <p className="text-xs tracking-wide text-muted-foreground uppercase">
                  Action timeline
                </p>
                <div className="mt-4">
                  <Timeline actions={recovery.actions ?? []} recovery={recovery} />
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  disabled={control.isPending}
                  onClick={() => control.mutate({ id: recovery.id, action: "pause" })}
                >
                  <Pause className="size-4" /> Pause
                </Button>
                <Button
                  disabled={control.isPending}
                  onClick={() => control.mutate({ id: recovery.id, action: "resume" })}
                >
                  <Play className="size-4" /> Resume
                </Button>
              </div>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm">{value}</p>
    </div>
  );
}

function RecoveriesPage() {
  const [selected, setSelected] = useState<Recovery | null>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ["recoveries"],
    queryFn: () => api.recoveries(),
    retry: false,
  });

  return (
    <AppLayout
      title="Recoveries"
      subtitle="Every recovery run the agent is working, with its full evidence trail"
    >
      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : error ? (
        <ErrorState message={(error as Error).message} />
      ) : !data || data.recoveries.length === 0 ? (
        <EmptyState
          title="No recoveries yet"
          description="Once a failed payment arrives, the agent opens a recovery run and it shows up here."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface text-left text-xs tracking-wide text-muted-foreground uppercase">
                <th className="px-4 py-3 font-medium">Payment</th>
                <th className="px-4 py-3 font-medium">Root cause</th>
                <th className="px-4 py-3 font-medium">Confidence</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Strategy</th>
                <th className="px-4 py-3 font-medium">Attempts</th>
                <th className="px-4 py-3 font-medium">Next action</th>
              </tr>
            </thead>
            <tbody>
              {data.recoveries.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className="cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-surface"
                >
                  <td className="num px-4 py-3 text-xs">
                    {r.payment?.razorpay_payment_id ?? r.payment_id}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status="neutral" label={titleCase(r.root_cause)} />
                  </td>
                  <td className="px-4 py-3">
                    <Confidence value={r.root_cause_confidence} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      status={r.status}
                      label={r.status === "escalated" ? "Review Req." : undefined}
                    />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {titleCase(r.current_strategy)}
                  </td>
                  <td className="num px-4 py-3">
                    {r.attempt_count}/{r.max_attempts}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    <span>{titleCase(r.next_action)}</span>
                    {r.next_action_at ? (
                      <span className="num block text-xs">
                        {formatDateTime(r.next_action_at)}
                      </span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <DetailSheet recovery={selected} onClose={() => setSelected(null)} />
    </AppLayout>
  );
}
