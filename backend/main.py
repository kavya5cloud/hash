"""Deployment entrypoint for the Hash API.

Vercel resolves a Python service from a conventional entry module, so this
re-exports the FastAPI application defined in `hash_market.api`.
"""

from hash_market.api import app


__all__ = ["app"]
