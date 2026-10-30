# Hash

Hash is a market where NVIDIA Nemotron models of different sizes bid for tasks, get verified and paid, and build reputation, so every job goes to the cheapest model that can actually do it.

## How it works

Hash separates model reasoning from deterministic market mechanics:

1. A Manager Nemotron decomposes a goal into a task.
2. Eligible Worker Nemotrons submit sealed bids.
3. Hash deterministically awards the task using price and reputation.
4. Credits are escrowed before work begins.
5. The winning Worker executes the task.
6. A Verifier Nemotron checks the submitted work.
7. Settlement releases payment or applies deterministic slashing.
8. The ledger records the market lifecycle and model telemetry.

Models make decisions about tasks and work. Money moves only through deterministic market code.

## Architecture

```text
                         HASH
                           |
                    +------v------+
                    |   Manager   |
                    |  Nemotron   |
                    +------+-------+
                           |
                          Task
                           |
                    +------v------+
                    | Sealed Bids |
                    +------+-------+
                           |
             +-------------+-------------+
             |             |             |
        Worker Nano   Worker Lightning   Worker ...
             |             |             |
             +-------------+-------------+
                           |
                    Deterministic
                    Market Award
                           |
                         Escrow
                           |
                    +------v------+
                    |   Worker    |
                    |  Execution  |
                    +------+------+
                           |
                    +------v------+
                    |   Verifier  |
                    |  Nemotron   |
                    +------+------+
                           |
                    Settlement /
                    Slashing /
                    Reputation
                           |
                    +------v------+
                    |   Ledger    |
                    +-------------+
```

## Why the name Hash?

“Hash” refers to the idea of hashing something out: models compete, work is verified, and the market resolves which model should handle a task. It also nods to the computing concept of a hash/fingerprint.

Hash is **not a cryptocurrency, blockchain, or real-money marketplace**. Its credits are internal accounting units used to demonstrate deterministic market mechanics.


## Quickstart

Hash needs a Nebius Token Factory API key for live runs. Copy the example
environment file and fill it in:

```bash
cp .env.example .env    # set NEBIUS_API_KEY
```

Install and start the API:

```bash
make setup
make dev                # http://127.0.0.1:8000
```

Start the dashboard in a second terminal:

```bash
cd frontend
npm install
npm run dev             # http://localhost:3000
```

Without an API key, `GET /demo/run` and the dashboard's "Recorded demo" button
still work: they replay the pre-recorded run in `demo/` and never call a model.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Service health |
| `GET /agents` | Worker pool with reputation, awards, and win rates |
| `POST /runs` | Run the full market lifecycle for a goal |
| `GET /runs` | Compact list of past runs |
| `GET /runs/{run_id}` | Structured run rebuilt from the ledger |
| `GET /runs/{run_id}/events` | Ledger events as Server-Sent Events |
| `GET /benchmark` | Latest monolith-vs-market benchmark results |
| `GET /demo/run` | Recorded demo run (no model calls, no ledger writes) |
| `GET /models` | Models available from Nebius Token Factory |

## Landing page and dashboard

`frontend/` serves two things:

| Route | What it is |
|---|---|
| `/` | The Hash landing page, a prebuilt static export in `frontend/public/` |
| `/market` | The live market dashboard (Next.js app router) |

Next does not serve nested `public/` directories as clean routes, so `/` and
the landing page's own routes are rewritten onto their static files in
`frontend/next.config.ts`.

The dashboard renders one run end to end — task, sealed bids, deterministic
award, escrow, verification, settlement, per-model telemetry, and the
append-only ledger — alongside the worker pool, the benchmark comparison, and
past runs. It is styled from the landing page's palette so the two read as one
product. See [frontend/README.md](frontend/README.md).

## Benchmark

The benchmark runs 20 self-contained Python coding tasks with hidden pytest
verification, comparing a monolith (largest Nemotron, one retry) against the
Hash market:

```bash
make benchmark
```

Results are written to `benchmark_results.json` and served by `GET /benchmark`.
The latest recorded comparison is in [SUBMISSION.md](SUBMISSION.md).

## Tests

```bash
make test               # backend: pytest
cd frontend && npm run lint && npm run build
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `NEBIUS_API_KEY` | — | Nebius Token Factory API key, required for live runs |
| `HASH_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Browser origins allowed to call the API |
| `NEXT_PUBLIC_HASH_API` | `http://127.0.0.1:8000` | API base URL used by the dashboard |
