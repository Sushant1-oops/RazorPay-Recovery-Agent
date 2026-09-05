// Razorpay reports amounts in the smallest currency unit (paise for INR).
export function formatAmount(amount: number | null | undefined, currency = "INR") {
  if (amount == null) return "—";
  const major = amount / 100;
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      maximumFractionDigits: 2,
    }).format(major);
  } catch {
    return `${major.toFixed(2)} ${currency}`;
  }
}

export function formatPercent(value: number | null | undefined, alreadyPercent?: boolean) {
  if (value == null) return "—";
  if (value === 0) return "0.0%";
  const isAlready = alreadyPercent !== undefined ? alreadyPercent : value > 1.0;
  const pct = isAlready ? value : value * 100;
  return `${pct.toFixed(1)}%`;
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds == null || seconds <= 0) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export function titleCase(value: string | null | undefined) {
  if (!value) return "—";
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
