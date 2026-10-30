# Hash Demo Fallback

The recorded demo run now lives with the backend it is served from, at
`backend/hash_market/data/fallback_run.json`, so it ships inside the deployed
API bundle. It is served by `GET /demo/run` and shown by the dashboard's
"Recorded demo" button.

It is deterministic, pre-recorded data for a record-ready Hash demo.

The fallback does not call Nebius Token Factory and does not write to the market ledger.

It is intended only for demonstrations when live provider access is unavailable.

The data mirrors the shape of a completed Hash market run and is clearly labeled as recorded demo data.
