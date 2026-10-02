"""Append-only SQLite event ledger for Hash."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .models import LedgerEvent


class Ledger:
    """Persist immutable market events in SQLite."""

    def __init__(self, path: str | Path = "hash.db") -> None:
        """Initialize the ledger database."""
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp REAL NOT NULL,
                data TEXT NOT NULL
            )
            """
        )

        self.connection.commit()

    def append(
        self,
        run_id: str,
        event_type: str,
        data: dict | None = None,
    ) -> LedgerEvent:
        """Append one immutable event to the ledger."""

        event = LedgerEvent(
            run_id=run_id,
            event_type=event_type,
            timestamp=time.time(),
            data=data or {},
        )

        cursor = self.connection.execute(
            """
            INSERT INTO events (
                run_id,
                event_type,
                timestamp,
                data
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                event.run_id,
                event.event_type,
                event.timestamp,
                json.dumps(event.data),
            ),
        )

        self.connection.commit()

        event.id = cursor.lastrowid
        return event

    def events(self, run_id: str) -> list[LedgerEvent]:
        """Return all events for a run in insertion order."""

        rows = self.connection.execute(
            """
            SELECT id, run_id, event_type, timestamp, data
            FROM events
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        ).fetchall()

        return [
            LedgerEvent(
                id=row[0],
                run_id=row[1],
                event_type=row[2],
                timestamp=row[3],
                data=json.loads(row[4]),
            )
            for row in rows
        ]

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()
