// Single typed client for the FastAPI recovery-agent backend.
// No BaaS: plain fetch + JWT bearer tokens.

export const API_BASE_URL: string =
  (import.meta.env["VITE_API_BASE_URL"] as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

const TOKEN_KEY = "recovery_agent_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
};

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = opts;
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? null : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the recovery service.");
  }

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Session expired. Please sign in again.");
  }

  const text = await res.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const detail =
      (data as { detail?: unknown } | null)?.detail ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data as T;
}

/* ---------------------------------- types --------------------------------- */

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AnalyticsOverview {
  total_payments: number;
  successful_payments: number;
  failed_payments: number;
  recoverable_payments: number;
  recovered_payments: number;
  recovery_rate: number;
  total_recovered_revenue: number;
  average_recovery_time_seconds: number;
}

export interface FailureBreakdownItem {
  failure_type: string;
  count: number;
  percentage: number;
}

export interface RecoveryStrategyItem {
  strategy: string;
  count: number;
  success_rate: number;
}

export interface Payment {
  id: string;
  razorpay_payment_id: string;
  razorpay_order_id: string | null;
  customer_id: string | null;
  amount: number;
  currency: string;
  payment_method: string | null;
  status: string;
  failure_code: string | null;
  failure_reason: string | null;
  attempt_count: number;
  recovered: boolean;
  created_at: string;
  updated_at: string;
  recovery_id: string | null;
}

export interface RecoveryAction {
  id: string;
  action_type: string;
  action_status: string;
  reason: string | null;
  parameters: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface Recovery {
  id: string;
  payment_id: string;
  status: string;
  root_cause: string | null;
  root_cause_confidence: number | null;
  recoverability_score: number | null;
  current_strategy: string | null;
  current_step: string | null;
  attempt_count: number;
  max_attempts: number;
  next_action: string | null;
  next_action_at: string | null;
  recovered_at: string | null;
  explanation: string | null;
  created_at: string;
  updated_at: string;
  actions: RecoveryAction[];
  payment: Payment | null;
}

export interface RecoveryControlResponse {
  recovery_id: string;
  status: string;
  message: string;
}

/* -------------------------------- endpoints ------------------------------- */

export const api = {
  register: (email: string, password: string) =>
    request<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),

  overview: () => request<AnalyticsOverview>("/api/v1/analytics/overview"),

  failureBreakdown: () =>
    request<{ breakdown: FailureBreakdownItem[] }>("/api/v1/analytics/failure-breakdown"),

  recoveryStrategies: () =>
    request<{ strategies: RecoveryStrategyItem[] }>("/api/v1/analytics/recovery-strategies"),

  payments: () => request<{ payments: Payment[]; total: number }>("/api/v1/payments"),

  payment: (paymentId: string) => request<Payment>(`/api/v1/payments/${paymentId}`),

  recoveries: () => request<{ recoveries: Recovery[]; total: number }>("/api/v1/recoveries"),

  pauseRecovery: (id: string) =>
    request<RecoveryControlResponse>(`/api/v1/recoveries/${id}/pause`, { method: "POST" }),

  resumeRecovery: (id: string) =>
    request<RecoveryControlResponse>(`/api/v1/recoveries/${id}/resume`, { method: "POST" }),

  reviewRecovery: (id: string, decision: "approve_retry" | "reject" | "resolve", notes?: string) =>
    request<RecoveryControlResponse>(`/api/v1/recoveries/${id}/review`, {
      method: "POST",
      body: { decision, notes },
    }),

  health: () => request<unknown>("/health", { auth: false }),
};
