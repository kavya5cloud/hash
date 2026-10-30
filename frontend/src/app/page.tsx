"use client";

import { useCallback, useEffect, useState } from "react";

import {
  api,
  EVENT_LABELS,
  formatCredits,
  formatMs,
  formatUsd,
  type Agent,
  type Benchmark,
  type BenchmarkMode,
  type Run,
  type RunSummary,
  type Telemetry,
} from "@/lib/hash";

type Panel = {
  title: string;
  children: React.ReactNode;
  aside?: React.ReactNode;
};

function Panel({ title, children, aside }: Panel) {
  return (
    <section className="rounded-xl border border-black/10 bg-black/[0.015] p-5 dark:border-white/10 dark:bg-white/[0.02]">
      <header className="mb-4 flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold tracking-wide uppercase opacity-70">
          {title}
        </h2>
        {aside ? <div className="text-xs opacity-60">{aside}</div> : null}
      </header>
      {children}
    </section>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-black/10 p-3 dark:border-white/10">
      <div className="text-[11px] tracking-wide uppercase opacity-60">
        {label}
      </div>
      <div className="mt-1 font-mono text-sm">{value}</div>
    </div>
  );
}

function Pill({
  tone,
  children,
}: {
  tone: "pass" | "fail" | "neutral";
  children: React.ReactNode;
}) {
  const tones = {
    pass: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
    fail: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
    neutral: "bg-black/10 dark:bg-white/10",
  } as const;

  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function TelemetryRow({
  role,
  telemetry,
}: {
  role: string;
  telemetry: Telemetry | null | undefined;
}) {
  if (!telemetry) return null;

  return (
    <tr className="border-t border-black/5 dark:border-white/5">
      <td className="py-2 pr-4 font-medium">{role}</td>
      <td className="py-2 pr-4 font-mono text-xs break-all">
        {telemetry.model}
      </td>
      <td className="py-2 pr-4 text-right font-mono">
        {telemetry.total_tokens}
      </td>
      <td className="py-2 pr-4 text-right font-mono">
        {formatMs(telemetry.latency_ms)}
      </td>
      <td className="py-2 text-right font-mono">
        {formatUsd(telemetry.cost_usd)}
      </td>
    </tr>
  );
}

function BenchmarkTable({ benchmark }: { benchmark: Benchmark }) {
  const monolith = (benchmark.monolith ?? {}) as BenchmarkMode;
  const market = (benchmark.market ?? {}) as BenchmarkMode;

  const rows: [string, React.ReactNode, React.ReactNode][] = [
    ["Tasks", monolith.tasks ?? "—", market.tasks ?? "—"],
    ["Passed", monolith.passed ?? "—", market.passed ?? "—"],
    [
      "Pass rate",
      monolith.pass_rate !== undefined
        ? `${(monolith.pass_rate * 100).toFixed(0)}%`
        : "—",
      market.pass_rate !== undefined
        ? `${(market.pass_rate * 100).toFixed(0)}%`
        : "—",
    ],
    [
      "Token Factory cost",
      formatUsd(monolith.token_factory_cost_usd),
      formatUsd(market.token_factory_cost_usd),
    ],
    [
      "Average cost / task",
      formatUsd(monolith.average_cost_usd),
      formatUsd(market.average_cost_usd),
    ],
    [
      "Average latency",
      formatMs(monolith.average_latency_ms),
      formatMs(market.average_latency_ms),
    ],
    ["Retries", monolith.retries ?? "—", market.retries ?? "—"],
  ];

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-[11px] tracking-wide uppercase opacity-60">
          <th className="pb-2 font-medium">Metric</th>
          <th className="pb-2 text-right font-medium">Monolith</th>
          <th className="pb-2 text-right font-medium">Market</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, left, right]) => (
          <tr
            key={label}
            className="border-t border-black/5 dark:border-white/5"
          >
            <td className="py-2 pr-4">{label}</td>
            <td className="py-2 pr-4 text-right font-mono">{left}</td>
            <td className="py-2 text-right font-mono">{right}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Home() {
  const [goal, setGoal] = useState(
    "Write a Python function that reverses a string.",
  );
  const [run, setRun] = useState<Run | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [history, setHistory] = useState<RunSummary[]>([]);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      await api.health();
      setOnline(true);
    } catch {
      setOnline(false);
      return;
    }

    const [agentsResult, historyResult, benchmarkResult] =
      await Promise.allSettled([
        api.agents(),
        api.runs(),
        api.benchmark(),
      ]);

    if (agentsResult.status === "fulfilled") setAgents(agentsResult.value);
    if (historyResult.status === "fulfilled") setHistory(historyResult.value);
    if (benchmarkResult.status === "fulfilled") {
      setBenchmark(benchmarkResult.value);
    }
  }, []);

  useEffect(() => {
    // Deferred so the first paint is not blocked and state lands in a callback.
    void Promise.resolve().then(refresh);
  }, [refresh]);

  const withBusy = async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);

    try {
      await work();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const startRun = () =>
    withBusy(async () => {
      const created = await api.createRun(goal);
      setRun(await api.run(created.run_id));
      await refresh();
    });

  const loadDemo = () =>
    withBusy(async () => {
      setRun(await api.demoRun());
    });

  const openRun = (runId: string) =>
    withBusy(async () => {
      setRun(await api.run(runId));
    });

  const verdict = run?.verdicts?.[0];
  const task = run?.tasks?.[0];

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-10">
      <header className="mb-8">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Hash</h1>
          <Pill tone={online ? "pass" : online === null ? "neutral" : "fail"}>
            {online === null
              ? "checking API"
              : online
                ? "API online"
                : "API offline"}
          </Pill>
        </div>
        <p className="mt-2 max-w-2xl text-sm opacity-70">
          A market where NVIDIA Nemotron models bid for tasks, get verified and
          paid, and build reputation. Credits are internal accounting units, not
          money.
        </p>
      </header>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <input
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          placeholder="Describe a goal for the market"
          className="flex-1 rounded-lg border border-black/15 bg-transparent px-3 py-2 text-sm outline-none focus:border-black/40 dark:border-white/15 dark:focus:border-white/40"
        />
        <div className="flex gap-2">
          <button
            onClick={startRun}
            disabled={busy || !goal.trim() || online === false}
            className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-40"
          >
            {busy ? "Running…" : "Run market"}
          </button>
          <button
            onClick={loadDemo}
            disabled={busy || online === false}
            className="rounded-lg border border-black/15 px-4 py-2 text-sm font-medium disabled:opacity-40 dark:border-white/15"
          >
            Recorded demo
          </button>
        </div>
      </div>

      {error ? (
        <p className="mb-6 rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-700 dark:text-rose-300">
          {error}
        </p>
      ) : null}

      {online === false ? (
        <p className="mb-6 rounded-lg border border-black/10 px-3 py-2 text-sm opacity-70 dark:border-white/10">
          Start the backend with <code className="font-mono">make dev</code>,
          then reload.
        </p>
      ) : null}

      <div className="flex flex-col gap-6">
        {run ? (
          <>
            {run.demo ? (
              <p className="rounded-lg bg-amber-500/15 px-3 py-2 text-xs font-medium text-amber-800 dark:text-amber-200">
                {run.label ?? "Recorded demo data — not a live run."}
              </p>
            ) : null}

            <Panel
              title="Run"
              aside={<span className="font-mono">{run.run_id}</span>}
            >
              <p className="text-sm">{run.goal.prompt}</p>

              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Stat
                  label="Status"
                  value={
                    <Pill
                      tone={
                        run.status === "completed"
                          ? "pass"
                          : run.status === "failed"
                            ? "fail"
                            : "neutral"
                      }
                    >
                      {run.status}
                    </Pill>
                  }
                />
                <Stat
                  label="Task budget"
                  value={formatCredits(run.cost_summary.task_budget)}
                />
                <Stat
                  label="Winning price"
                  value={formatCredits(run.cost_summary.worker_price)}
                />
                <Stat
                  label="Token Factory cost"
                  value={formatUsd(
                    run.cost_summary.token_factory_cost_usd,
                  )}
                />
              </div>

              {task?.acceptance_criteria?.length ? (
                <div className="mt-4">
                  <div className="text-[11px] tracking-wide uppercase opacity-60">
                    Acceptance criteria
                  </div>
                  <ul className="mt-1 list-disc pl-5 text-sm">
                    {task.acceptance_criteria.map((criterion) => (
                      <li key={criterion}>{criterion}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </Panel>

            <Panel
              title="Sealed bids"
              aside={
                run.award
                  ? `awarded to ${run.award.worker_id} · score ${run.award.score?.toFixed(3)}`
                  : "no award"
              }
            >
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] tracking-wide uppercase opacity-60">
                    <th className="pb-2 font-medium">Worker</th>
                    <th className="pb-2 text-right font-medium">Price</th>
                    <th className="pb-2 text-right font-medium">Est. time</th>
                    <th className="pb-2 pl-4 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {run.bids.map((bid, index) => (
                    <tr
                      key={bid.bid_id ?? `${bid.worker_id}-${index}`}
                      className="border-t border-black/5 dark:border-white/5"
                    >
                      <td className="py-2 pr-4">
                        <div className="font-medium">{bid.worker_id}</div>
                        {bid.plan ? (
                          <div className="text-xs opacity-60">{bid.plan}</div>
                        ) : null}
                        {bid.reason ? (
                          <div className="text-xs opacity-60">
                            {bid.reason}
                          </div>
                        ) : null}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono">
                        {formatCredits(bid.price)}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono">
                        {bid.estimated_time_seconds !== null
                          ? `${bid.estimated_time_seconds}s`
                          : "—"}
                      </td>
                      <td className="py-2 pl-4">
                        <Pill
                          tone={
                            bid.worker_id === run.award?.worker_id
                              ? "pass"
                              : bid.status === "rejected"
                                ? "fail"
                                : "neutral"
                          }
                        >
                          {bid.worker_id === run.award?.worker_id
                            ? "awarded"
                            : bid.status}
                        </Pill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {run.award ? (
                <p className="mt-3 text-xs opacity-60">
                  Award score combines price ({run.award.price_component}) and
                  reputation ({run.award.reputation_component})
                  deterministically.
                </p>
              ) : null}
            </Panel>

            {verdict ? (
              <Panel
                title="Verification and settlement"
                aside={
                  <Pill tone={verdict.passed ? "pass" : "fail"}>
                    {verdict.passed ? "passed" : "failed"}
                  </Pill>
                }
              >
                <p className="text-sm">{verdict.reason}</p>

                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <Stat
                    label="Escrow"
                    value={formatCredits(run.escrow?.amount)}
                  />
                  <Stat
                    label={
                      run.settlement?.type === "payment_slashed"
                        ? "Slashed"
                        : "Paid"
                    }
                    value={formatCredits(run.settlement?.amount)}
                  />
                  <Stat label="Worker" value={verdict.worker_id ?? "—"} />
                </div>

                {run.output ? (
                  <pre className="mt-4 max-h-72 overflow-auto rounded-lg bg-black/5 p-3 font-mono text-xs dark:bg-white/5">
                    {run.output}
                  </pre>
                ) : null}
              </Panel>
            ) : null}

            <Panel title="Model telemetry">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] tracking-wide uppercase opacity-60">
                    <th className="pb-2 font-medium">Role</th>
                    <th className="pb-2 font-medium">Model</th>
                    <th className="pb-2 text-right font-medium">Tokens</th>
                    <th className="pb-2 text-right font-medium">Latency</th>
                    <th className="pb-2 text-right font-medium">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  <TelemetryRow role="Manager" telemetry={run.telemetry.manager} />
                  {run.telemetry.bids.map((telemetry, index) => (
                    <TelemetryRow
                      key={`bid-${index}`}
                      role={`Bidder ${index + 1}`}
                      telemetry={telemetry}
                    />
                  ))}
                  <TelemetryRow role="Worker" telemetry={run.telemetry.worker} />
                  <TelemetryRow
                    role="Verifier"
                    telemetry={run.telemetry.verifier}
                  />
                </tbody>
              </table>
            </Panel>

            <Panel
              title="Ledger"
              aside={`${run.events.length} append-only events`}
            >
              <ol className="flex flex-col gap-2">
                {run.events.map((event) => (
                  <li
                    key={event.id}
                    className="flex gap-3 border-l-2 border-black/10 pl-3 text-sm dark:border-white/10"
                  >
                    <span className="w-6 shrink-0 font-mono text-xs opacity-50">
                      {event.id}
                    </span>
                    <span className="font-medium">
                      {EVENT_LABELS[event.event_type] ?? event.event_type}
                    </span>
                    <span className="ml-auto truncate font-mono text-xs opacity-50">
                      {Object.entries(event.data)
                        .slice(0, 2)
                        .map(([key, value]) => `${key}=${String(value)}`)
                        .join(" ")}
                    </span>
                  </li>
                ))}
              </ol>
            </Panel>
          </>
        ) : (
          <Panel title="Run">
            <p className="text-sm opacity-70">
              Start a market run, or load the recorded demo, to see bidding,
              verification, settlement, and the ledger.
            </p>
          </Panel>
        )}

        <Panel title="Worker pool">
          {agents.length ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] tracking-wide uppercase opacity-60">
                  <th className="pb-2 font-medium">Worker</th>
                  <th className="pb-2 font-medium">Model</th>
                  <th className="pb-2 text-right font-medium">Reputation</th>
                  <th className="pb-2 text-right font-medium">Awards</th>
                  <th className="pb-2 text-right font-medium">Win rate</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr
                    key={agent.id}
                    className="border-t border-black/5 dark:border-white/5"
                  >
                    <td className="py-2 pr-4">
                      <div className="font-medium">{agent.name}</div>
                      <div className="text-xs opacity-60">{agent.strategy}</div>
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs break-all">
                      {agent.model}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono">
                      {agent.reputation.toFixed(1)}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono">
                      {agent.awards}
                    </td>
                    <td className="py-2 text-right font-mono">
                      {`${(agent.win_rate * 100).toFixed(0)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm opacity-70">No worker data available.</p>
          )}
        </Panel>

        {benchmark ? (
          <Panel
            title="Benchmark"
            aside="monolith vs market, hidden pytest verification"
          >
            <BenchmarkTable benchmark={benchmark} />
          </Panel>
        ) : null}

        <Panel title="Past runs" aside={`${history.length} recorded`}>
          {history.length ? (
            <ul className="flex flex-col gap-1">
              {history.slice(0, 12).map((summary) => (
                <li key={summary.run_id}>
                  <button
                    onClick={() => openRun(summary.run_id)}
                    className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5"
                  >
                    <Pill
                      tone={
                        summary.passed === true
                          ? "pass"
                          : summary.passed === false
                            ? "fail"
                            : "neutral"
                      }
                    >
                      {summary.passed === true
                        ? "passed"
                        : summary.passed === false
                          ? "failed"
                          : "open"}
                    </Pill>
                    <span className="flex-1 truncate">
                      {summary.goal ?? summary.run_id}
                    </span>
                    <span className="font-mono text-xs opacity-50">
                      {summary.event_count} events
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm opacity-70">No runs recorded yet.</p>
          )}
        </Panel>
      </div>

      <footer className="mt-10 text-xs opacity-50">
        Hash is not a cryptocurrency, blockchain, or real-money marketplace.
      </footer>
    </main>
  );
}
