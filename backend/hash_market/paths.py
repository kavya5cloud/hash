"""Filesystem locations used by Hash.

Hash runs both as a local process and as a serverless function. Locally the
data files sit in the repository and the ledger is written next to it. In a
serverless environment the bundle is read-only except for a temporary
directory, so every location is overridable by environment variable and the
packaged data files are resolved relative to this module rather than the
current working directory.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"

DEMO_RUN_PATH = DATA_DIR / "fallback_run.json"
BENCHMARK_RESULTS_PATH = DATA_DIR / "benchmark_results.json"
BENCHMARK_CSV_PATH = DATA_DIR / "benchmark_results.csv"


def _read_only_filesystem() -> bool:
    """Report whether the deployment bundle is read-only."""

    return bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def ledger_path() -> Path:
    """Return the ledger database location.

    `HASH_DB_PATH` wins. Otherwise the ledger is written to the working
    directory, except on a read-only deployment, where it falls back to a
    temporary directory. A temporary ledger does not survive between
    invocations, so a deployed Hash records runs for the life of the instance
    only.
    """

    configured = os.environ.get("HASH_DB_PATH")

    if configured:
        return Path(configured)

    if _read_only_filesystem():
        return Path(tempfile.gettempdir()) / "hash.db"

    return Path("hash.db")


def benchmark_results_path() -> Path:
    """Return the benchmark results location, preferring a local override."""

    configured = os.environ.get("HASH_BENCHMARK_RESULTS_PATH")

    if configured:
        return Path(configured)

    return BENCHMARK_RESULTS_PATH
