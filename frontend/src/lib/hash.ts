// Deployed, the API is a service on the same origin behind /api. Locally it is
// a separate uvicorn process. NEXT_PUBLIC_HASH_API overrides both.
export const HASH_API =
  process.env.NEXT_PUBLIC_HASH_API ??
  (process.env.NODE_ENV === "production" ? "/api" : "http://127.0.0.1:8000");

export type Telemetry = {
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_usd: number | null;
  recorded_demo_data?: boolean;
};

export type Bid = {
  bid_id: string | null;
  worker_id: string;
  price: number | null;
  estimated_time_seconds: number | null;
  plan: string | null;
  status: string;
  reason?: string;
  telemetry?: Telemetry | null;
};

export type LedgerEvent = {
  id: number;
  run_id: string;
  event_type: string;
  timestamp: number;
  data: Record<string, unknown>;
};

export type Run = {
  run_id: string;
  status: "completed" | "failed" | "running";
  demo?: boolean;
  label?: string;
  goal: { id?: string; prompt?: string; budget?: number };
  tasks: {
    id?: string;
    type?: string;
    budget?: number;
    acceptance_criteria: string[];
  }[];
  bids: Bid[];
  award: {
    worker_id?: string;
    bid_id?: string;
    price?: number;
    score?: number;
    reputation_component?: number;
    price_component?: number;
  } | null;
  escrow: { worker_id?: string; amount?: number } | null;
  verdicts: {
    worker_id?: string;
    passed?: boolean;
    reason?: string;
  }[];
  output: string | null;
  settlement: {
    type: "payment_released" | "payment_slashed";
    worker_id?: string;
    amount?: number;
  } | null;
  reputation: Record<string, number>;
  telemetry: {
    manager: Telemetry | null;
    bids: Telemetry[];
    worker: Telemetry | null;
    verifier: Telemetry | null;
  };
  cost_summary: {
    task_budget: number | null;
    worker_price: number | null;
    total_tokens: number;
    token_factory_cost_usd: number | null;
    recorded_demo_data?: boolean;
  };
  events: LedgerEvent[];
};

export type Agent = {
  id: string;
  name: string;
  model: string;
  strategy: string;
  skills: string[];
  reputation: number;
  balance: number;
  awards: number;
  wins: number;
  win_rate: number;
};

export type RunSummary = {
  run_id: string;
  goal: string | null;
  passed: boolean | null;
  event_count: number;
};

export type BenchmarkMode = {
  tasks?: number;
  passed?: number;
  pass_rate?: number;
  token_factory_cost_usd?: number;
  average_cost_usd?: number;
  total_latency_ms?: number;
  average_latency_ms?: number;
  retries?: number;
};

export type Benchmark = Record<string, unknown> & {
  monolith?: BenchmarkMode;
  market?: BenchmarkMode;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${HASH_API}${path}`, {
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;

    try {
      const body = (await response.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // Response had no JSON body; keep the status text.
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  agents: () => request<Agent[]>("/agents"),
  runs: () => request<RunSummary[]>("/runs"),
  run: (runId: string) => request<Run>(`/runs/${runId}`),
  demoRun: () => request<Run>("/demo/run"),
  benchmark: () => request<Benchmark>("/benchmark"),
  createRun: (goal: string) =>
    request<{ run_id: string; passed: boolean | null; verdict: string | null }>(
      "/runs",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal }),
      },
    ),
};

export const EVENT_LABELS: Record<string, string> = {
  goal_created: "Goal created",
  task_posted: "Task posted",
  sealed_bid_submitted: "Sealed bid submitted",
  bid_failed: "Bid rejected",
  task_awarded: "Task awarded",
  escrow_reserved: "Escrow reserved",
  work_submitted: "Work submitted",
  verdict: "Verifier verdict",
  payment_released: "Payment released",
  payment_slashed: "Payment slashed",
  reputation_updated: "Reputation updated",
  goal_completed: "Goal completed",
  goal_failed: "Goal failed",
};

export function formatUsd(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value === 0) return "$0";
  return `$${value.toFixed(8).replace(/0+$/, "").replace(/\.$/, "")}`;
}

export function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 0 })} ms`;
}

export function formatCredits(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 4 })} cr`;
}
