# Hash — Decisions

## 2026-10-02

- Project name: Hash.
- Backend: Python 3.11+ with FastAPI.
- Initial persistence: SQLite append-only event ledger.
- LLM provider: Nebius Token Factory.
- Model family: NVIDIA Nemotron.
- No model IDs will be invented; available IDs will be discovered from the Token Factory `/v1/models` endpoint.
- Market accounting uses in-market credits, not real money or cryptocurrency.
