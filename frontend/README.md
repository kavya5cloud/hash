# Hash Frontend

A Next.js dashboard for the Hash market.

It shows one market run end to end — task, sealed bids, deterministic award,
escrow, verification, settlement, model telemetry, and the append-only ledger —
plus the worker pool, the monolith-vs-market benchmark, and past runs.

## Run it

The dashboard reads the Hash API over HTTP, so start the backend first:

```bash
cd .. && make dev        # FastAPI on http://127.0.0.1:8000
```

Then:

```bash
npm install
npm run dev              # dashboard on http://localhost:3000
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_HASH_API` | `http://127.0.0.1:8000` | Hash API base URL |

The backend allows browser requests from `http://localhost:3000` and
`http://127.0.0.1:3000`. Override with `HASH_ALLOWED_ORIGINS` (comma separated)
when serving the dashboard from another origin.

## What it calls

| Endpoint | Used for |
|---|---|
| `GET /health` | API online indicator |
| `POST /runs` | Start a live market run |
| `GET /runs/{run_id}` | Full structured run from the ledger |
| `GET /runs` | Past runs list |
| `GET /agents` | Worker pool, reputation, win rates |
| `GET /benchmark` | Monolith vs market benchmark |
| `GET /demo/run` | Recorded demo run (no model calls) |

"Recorded demo" loads the pre-recorded fixture in `../demo/`. It is labeled in
the UI as recorded data and never calls a model.

## Checks

```bash
npm run lint
npm run build
```
