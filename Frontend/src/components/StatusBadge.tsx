import { cn } from "@/lib/utils";
import { titleCase } from "@/lib/format";

type Tone = "success" | "progress" | "danger" | "warning" | "neutral";

const TONE_MAP: Record<string, Tone> = {
  recovered: "success",
  captured: "success",
  success: "success",
  successful: "success",
  paid: "success",
  completed: "success",
  in_progress: "progress",
  in_recovery: "progress",
  analyzing: "progress",
  pending: "progress",
  scheduled: "progress",
  retrying: "progress",
  paused: "progress",
  waiting: "progress",
  failed: "danger",
  exhausted: "danger",
  escalated: "warning",
  requires_review: "warning",
  abandoned: "danger",
  cancelled: "danger",
  error: "danger",
};

export function statusTone(status: string | null | undefined): Tone {
  if (!status) return "neutral";
  return TONE_MAP[status.toLowerCase().replace(/[\s-]+/g, "_")] ?? "neutral";
}

const toneClass: Record<Tone, string> = {
  success: "bg-success-soft text-success border-success/25",
  progress: "bg-progress-soft text-progress border-progress/25",
  danger: "bg-danger-soft text-danger border-danger/25",
  warning: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  neutral: "bg-muted text-muted-foreground border-border",
};

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: string | null | undefined;
  label?: string;
  className?: string;
}) {
  const tone = statusTone(status);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium tracking-tight whitespace-nowrap",
        toneClass[tone],
        className,
      )}
    >
      <span className="size-1.5 rounded-full bg-current opacity-70" />
      {label ?? titleCase(status)}
    </span>
  );
}

export function YesNoBadge({ value }: { value: boolean }) {
  return <StatusBadge status={value ? "recovered" : "failed"} label={value ? "Yes" : "No"} />;
}
