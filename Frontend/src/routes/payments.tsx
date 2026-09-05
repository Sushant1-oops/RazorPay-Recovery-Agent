import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { api } from "@/lib/api";
import { titleCase } from "@/lib/format";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { AppLayout, EmptyState, ErrorState } from "@/components/AppLayout";
import { StatusBadge, YesNoBadge } from "@/components/StatusBadge";
import { formatAmount, formatDateTime } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/payments")({
  head: () => ({
    meta: [
      { title: "Payments — Recovery Agent Ops" },
      {
        name: "description",
        content:
          "Every captured and failed Razorpay payment with failure reasons, attempt counts and recovery status.",
      },
      { property: "og:title", content: "Payments — Recovery Agent Ops" },
      {
        property: "og:description",
        content: "Failed and captured payments with recovery status.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: PaymentsPage,
});

function PaymentDetail({ id, onClose }: { id: string | null; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["payment", id],
    queryFn: () => api.payment(id as string),
    enabled: !!id,
    retry: false,
  });

  return (
    <Sheet open={!!id} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="num text-sm">
            {data?.razorpay_payment_id ?? "Payment"}
          </SheetTitle>
          <SheetDescription>
            {data ? formatDateTime(data.created_at) : "Loading payment details"}
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 px-4 pb-8">
          {isLoading ? (
            <Skeleton className="h-40 w-full rounded-md" />
          ) : error ? (
            <ErrorState message={(error as Error).message} />
          ) : data ? (
            <>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={data.recovered ? "recovered" : data.status} />
                <YesNoBadge value={data.recovered} />
              </div>
              <dl className="grid gap-3 sm:grid-cols-2 text-sm">
                <Row label="Amount" value={formatAmount(data.amount, data.currency)} />
                <Row label="Method" value={titleCase(data.payment_method)} />
                <Row label="Order ID" value={data.razorpay_order_id ?? "—"} />
                <Row label="Customer" value={data.customer_id ?? "—"} />
                <Row label="Failure code" value={data.failure_code ?? "—"} />
                <Row label="Attempts" value={String(data.attempt_count)} />
                <Row label="Last update" value={formatDateTime(data.updated_at)} />
              </dl>
              <p className="rounded-md border border-border bg-surface p-3 text-sm text-muted-foreground">
                {data.failure_reason ?? "No failure reason reported."}
              </p>
            </>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5">{value}</dd>
    </div>
  );
}

function PaymentsPage() {
  const navigate = useNavigate();
  const [detailId, setDetailId] = useState<string | null>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ["payments"],
    queryFn: () => api.payments(),
    retry: false,
  });

  return (
    <AppLayout
      title="Payments"
      subtitle={data ? `${data.total} payment${data.total === 1 ? "" : "s"} ingested` : undefined}
    >
      {isLoading ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : error ? (
        <ErrorState message={(error as Error).message} />
      ) : !data || data.payments.length === 0 ? (
        <EmptyState
          title="No payments yet"
          description="Payments appear here as soon as Razorpay webhooks start reaching the backend."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface text-left text-xs tracking-wide text-muted-foreground uppercase">
                <th className="px-4 py-3 font-medium">Payment ID</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Failure reason</th>
                <th className="px-4 py-3 font-medium">Attempts</th>
                <th className="px-4 py-3 font-medium">Recovered</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.payments.map((p) => {
                const row = (
                  <>
                    <td className="num px-4 py-3 text-xs">{p.razorpay_payment_id}</td>
                    <td className="num px-4 py-3">{formatAmount(p.amount, p.currency)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={p.recovered ? "recovered" : p.status} />
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-muted-foreground">
                      {p.failure_reason ?? "—"}
                    </td>
                    <td className="num px-4 py-3">{p.attempt_count}</td>
                    <td className="px-4 py-3">
                      <YesNoBadge value={p.recovered} />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDateTime(p.created_at)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <ChevronRight className="size-4" />
                    </td>
                  </>
                );
                return (
                  <tr
                    key={p.id}
                    className="cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-surface"
                    onClick={() => {
                      if (p.recovery_id) {
                        void navigate({ to: "/recoveries" });
                      } else {
                        setDetailId(p.id);
                      }
                    }}
                  >
                    {row}
                  </tr>
                );

              })}
            </tbody>
          </table>
        </div>
      )}

      {data && data.payments.length > 0 ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Rows with an active recovery link through to the{" "}
          <Link to="/recoveries" className="underline underline-offset-4">
            recoveries
          </Link>{" "}
          evidence trail.
        </p>
      ) : null}

      <PaymentDetail id={detailId} onClose={() => setDetailId(null)} />
    </AppLayout>
  );
}
