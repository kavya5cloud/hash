# Hash — Submission Pack

## Problem

AI model selection is usually configured statically: a developer chooses one model and sends work to it. That makes it difficult to dynamically balance capability, cost, verification, and model reputation on a task-by-task basis.

## Audience

Hash is designed for developers and AI systems that need to route coding and other agent tasks across multiple models while keeping the routing and economic mechanics deterministic and observable.

## What Hash Does

Hash is a market where NVIDIA Nemotron models of different sizes bid for tasks, get verified and paid, and build reputation.

The core flow is:

1. A Manager Nemotron decomposes a goal into a task.
2. Eligible Worker Nemotrons submit sealed bids.
3. Hash deterministically awards the task using price and reputation.
4. Credits are escrowed before work begins.
5. The winning Worker executes the task.
6. A separate Verifier Nemotron checks the submitted work.
7. Deterministic settlement releases payment or applies slashing.
8. The ledger records the market lifecycle and model telemetry.

Models make decisions about tasks and work. Money moves only through deterministic market code.

## Nebius Token Factory + NVIDIA Nemotron

All model calls are routed through the Nebius Token Factory OpenAI-compatible API.

Hash uses these NVIDIA Nemotron model IDs:

| Role | Model |
|---|---|
| Manager | `nvidia/nemotron-3-super-120b-a12b` |
| Worker | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| Worker | `nvidia/Nemotron-3_5-Lightning` |
| Worker | `nvidia/nemotron-3-super-120b-a12b` |
| Verifier | `nvidia/Nemotron-3-Ultra-550b-a55b` |

Hash records model identity, token usage, latency, and Token Factory cost for model calls.

## Benchmark

The benchmark contains 20 self-contained Python coding tasks with hidden pytest verification.

Two modes are compared:

- **Monolith:** the largest Nemotron solves each task directly, with one retry available.
- **Market:** Hash runs each task through its market flow, where models compete for the task and the selected Worker is verified.

Latest recorded benchmark:

| Metric | Monolith | Market |
|---|---:|---:|
| Tasks | 20 | 20 |
| Passed | 20 | 20 |
| Pass rate | 100% | 100% |
| Token Factory cost | $0.0214902 | $0.02338146 |
| Average cost/task | $0.00107451 | $0.00116907 |
| Total latency | 61,038.50 ms | 59,028.89 ms |
| Average latency | 3,051.93 ms | 2,951.44 ms |
| Retries | 0 | 0 |

The latest market benchmark selected `worker-nano` for all 20 tasks.

These are recorded benchmark results from the current implementation, not projected or simulated performance claims.

## How It Was Built

- Python 3.11
- FastAPI
- Nebius Token Factory OpenAI-compatible API
- NVIDIA Nemotron models
- pytest hidden-test verification
- Append-only market ledger
- Deterministic market settlement
- SSE run-event streaming
- Configurable Token Factory pricing
- Next.js dashboard over the Hash API
- Static landing page served from the same deployment

## Dashboard

`frontend/` serves the Hash landing page at `/` and the live market dashboard
at `/market`.

The dashboard renders a single run end to end — task, sealed bids,
deterministic award, escrow, verification, settlement, per-model telemetry, and
the append-only ledger — plus the worker pool with reputation and win rates,
the benchmark comparison, and past runs. It shares the landing page's palette
and label treatment.

A recorded demo run is included for environments without Token Factory access.
It is labeled as recorded data in the UI, makes no model calls, and writes no
ledger events.

## Architecture

```text
                    HASH
                      |
                  Manager
                 Nemotron
                      |
                     Task
                      |
                Sealed Bids
                      |
          +-----------+-----------+
          |           |           |
       Worker       Worker      Worker
        Nano      Lightning     Super
          |           |           |
          +-----------+-----------+
                      |
             Deterministic Award
                      |
                    Escrow
                      |
                  Execution
                      |
                  Verifier
                  Nemotron
                      |
             Settlement / Slashing
                      |
                   Ledger
```
